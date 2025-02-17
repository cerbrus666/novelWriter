"""
novelWriter – GUI Document Viewer Panel
=======================================

File History:
Created: 2023-11-14 [2.2rc1] GuiDocViewerPanel

This file is a part of novelWriter
Copyright 2018–2023, Veronica Berglyd Olsen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import annotations

import logging

from enum import Enum

from PyQt5.QtCore import QModelIndex, QSize, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QHeaderView, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget
)

from novelwriter import CONFIG, SHARED
from novelwriter.enum import nwDocMode, nwItemClass
from novelwriter.common import checkInt
from novelwriter.constants import nwHeaders, nwLabels, nwLists, trConst
from novelwriter.core.index import IndexHeading, IndexItem

logger = logging.getLogger(__name__)


class GuiDocViewerPanel(QWidget):

    openDocumentRequest = pyqtSignal(str, Enum, str, bool)
    loadDocumentTagRequest = pyqtSignal(str, Enum)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)

        logger.debug("Create: GuiDocViewerPanel")

        self._lastHandle = None

        self.tabBackRefs = _ViewPanelBackRefs(self)

        self.mainTabs = QTabWidget(self)
        self.mainTabs.addTab(self.tabBackRefs, self.tr("References"))

        self.kwTabs: dict[str, _ViewPanelKeyWords] = {}
        self.idTabs: dict[str, int] = {}
        for itemClass in nwLists.USER_CLASSES:
            cTab = _ViewPanelKeyWords(self, itemClass)
            tabId = self.mainTabs.addTab(cTab, trConst(nwLabels.CLASS_NAME[itemClass]))
            self.kwTabs[itemClass.name] = cTab
            self.idTabs[itemClass.name] = tabId

        # Assemble
        self.outerBox = QVBoxLayout()
        self.outerBox.addWidget(self.mainTabs)
        self.outerBox.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.outerBox)
        self.updateTheme(updateTabs=False)

        logger.debug("Ready: GuiDocViewerPanel")

        return

    ##
    #  Methods
    ##

    def updateTheme(self, updateTabs: bool = True) -> None:
        """Update theme elements."""
        vPx = CONFIG.pxInt(4)
        lPx = CONFIG.pxInt(2)
        rPx = CONFIG.pxInt(14)
        hCol = self.palette().highlight().color()

        styleSheet = (
            "QTabWidget::pane {border: 0;} "
            "QTabWidget QTabBar::tab {"
            f"border: 0; padding: {vPx}px {rPx}px {vPx}px {lPx}px;"
            "} "
            "QTabWidget QTabBar::tab:selected {"
            f"color: rgb({hCol.red()}, {hCol.green()}, {hCol.blue()});"
            "} "
        )
        self.mainTabs.setStyleSheet(styleSheet)
        self.updateHandle(self._lastHandle)

        if updateTabs:
            self.tabBackRefs.updateTheme()
            for tab in self.kwTabs.values():
                tab.updateTheme()

        return

    def openProjectTasks(self) -> None:
        """Run open project tasks."""
        widths = SHARED.project.options.getValue("GuiDocViewerPanel", "colWidths", {})
        if isinstance(widths, dict):
            for key, value in widths.items():
                if key in self.kwTabs and isinstance(value, list):
                    self.kwTabs[key].setColumnWidths(value)
        return

    def closeProjectTasks(self) -> None:
        """Run close project tasks."""
        widths = {}
        for key, tab in self.kwTabs.items():
            widths[key] = tab.getColumnWidths()
        logger.debug("Saving State: GuiDocViewerPanel")
        SHARED.project.options.setValue("GuiDocViewerPanel", "colWidths", widths)
        return

    ##
    #  Public Slots
    ##

    @pyqtSlot()
    def indexWasCleared(self) -> None:
        """Handle event when the index has been cleared of content."""
        self.tabBackRefs.clearContent()
        for cTab in self.kwTabs.values():
            cTab.clearContent()
        return

    @pyqtSlot()
    def indexHasAppeared(self) -> None:
        """Handle event when the index has appeared."""
        for key, name, tClass, iItem, hItem in SHARED.project.index.getTagsData():
            if tClass in self.kwTabs and iItem and hItem:
                self.kwTabs[tClass].addUpdateEntry(key, name, iItem, hItem)
        self._updateTabVisibility()
        self.updateHandle(self._lastHandle)
        return

    @pyqtSlot(str)
    def projectItemChanged(self, tHandle: str) -> None:
        """Update meta data for project item."""
        self.tabBackRefs.refreshDocument(tHandle)
        for key in SHARED.project.index.getDocumentTags(tHandle):
            name, tClass, iItem, hItem = SHARED.project.index.getSingleTag(key)
            if tClass in self.kwTabs and iItem and hItem:
                self.kwTabs[tClass].addUpdateEntry(key, name, iItem, hItem)
        return

    @pyqtSlot(str)
    def updateHandle(self, tHandle: str | None) -> None:
        """Update the document handle."""
        self._lastHandle = tHandle
        self.tabBackRefs.refreshContent(tHandle or None)
        return

    @pyqtSlot(list, list)
    def updateChangedTags(self, updated: list[str], deleted: list[str]) -> None:
        """Forward tags changes to the lists."""
        for key in updated:
            name, tClass, iItem, hItem = SHARED.project.index.getSingleTag(key)
            if tClass in self.kwTabs and iItem and hItem:
                self.kwTabs[tClass].addUpdateEntry(key, name, iItem, hItem)
        for key in deleted:
            for cTab in self.kwTabs.values():
                if cTab.removeEntry(key):
                    break
            else:
                logger.warning("Could not remove tag '%s' from view panel", key)
        self._updateTabVisibility()
        return

    ##
    #  Internal Functions
    ##

    def _updateTabVisibility(self) -> None:
        """Hide class tabs with no content."""
        if CONFIG.verQtValue >= 0x050f00:
            for tClass, cTab in self.kwTabs.items():
                self.mainTabs.setTabVisible(self.idTabs[tClass], cTab.countEntries() > 0)
        return

# END Class GuiDocViewerPanel


class _ViewPanelBackRefs(QTreeWidget):

    C_DATA  = 0
    C_DOC   = 0
    C_EDIT  = 1
    C_VIEW  = 2
    C_TITLE = 3

    D_HANDLE = Qt.ItemDataRole.UserRole

    def __init__(self, parent: GuiDocViewerPanel) -> None:
        super().__init__(parent=parent)

        self._parent = parent
        self._treeMap: dict[str, QTreeWidgetItem] = {}

        iPx = SHARED.theme.baseIconSize
        cMg = CONFIG.pxInt(6)

        self.setHeaderLabels([self.tr("Document"), "", "", self.tr("First Heading")])
        self.setIndentation(0)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setIconSize(QSize(iPx, iPx))
        self.setFrameStyle(QFrame.Shape.NoFrame)

        # Set Header Sizes
        treeHeader = self.header()
        treeHeader.setStretchLastSection(True)
        treeHeader.setMinimumSectionSize(iPx + cMg)  # See Issue #1627
        treeHeader.setSectionResizeMode(self.C_DOC, QHeaderView.ResizeMode.ResizeToContents)
        treeHeader.setSectionResizeMode(self.C_EDIT, QHeaderView.ResizeMode.Fixed)
        treeHeader.setSectionResizeMode(self.C_VIEW, QHeaderView.ResizeMode.Fixed)
        treeHeader.setSectionResizeMode(self.C_TITLE, QHeaderView.ResizeMode.ResizeToContents)
        treeHeader.resizeSection(self.C_EDIT, iPx + cMg)
        treeHeader.resizeSection(self.C_VIEW, iPx + cMg)
        treeHeader.setSectionsMovable(False)

        # Cache Icons Locally
        self._editIcon = SHARED.theme.getIcon("edit")
        self._viewIcon = SHARED.theme.getIcon("view")

        # Signals
        self.clicked.connect(self._treeItemClicked)
        self.doubleClicked.connect(self._treeItemDoubleClicked)

        return

    def updateTheme(self) -> None:
        """Update theme elements."""
        self._editIcon = SHARED.theme.getIcon("edit")
        self._viewIcon = SHARED.theme.getIcon("view")
        for i in range(self.topLevelItemCount()):
            if item := self.topLevelItem(i):
                item.setIcon(self.C_EDIT, self._editIcon)
                item.setIcon(self.C_VIEW, self._viewIcon)
        return

    def clearContent(self) -> None:
        """Clear the widget."""
        self.clear()
        self._treeMap = {}
        return

    def refreshContent(self, dHandle: str | None) -> None:
        """Update the content."""
        self.clearContent()
        if dHandle:
            refs = SHARED.project.index.getBackReferenceList(dHandle)
            for tHandle, (sTitle, hItem) in refs.items():
                self._setTreeItemValues(tHandle, sTitle, hItem)
        return

    def refreshDocument(self, tHandle: str) -> None:
        """Refresh document meta data."""
        if iItem := SHARED.project.index.getItemData(tHandle):
            for sTitle, hItem in iItem.items():
                if f"{tHandle}:{sTitle}" in self._treeMap:
                    self._setTreeItemValues(tHandle, sTitle, hItem)
        return

    ##
    #  Private Slots
    ##

    @pyqtSlot("QModelIndex")
    def _treeItemClicked(self, index: QModelIndex) -> None:
        """Emit document open signal on user click."""
        tHandle = index.siblingAtColumn(self.C_DATA).data(self.D_HANDLE)
        if index.column() == self.C_EDIT:
            self._parent.openDocumentRequest.emit(tHandle, nwDocMode.EDIT, "", True)
        elif index.column() == self.C_VIEW:
            self._parent.openDocumentRequest.emit(tHandle, nwDocMode.VIEW, "", True)
        return

    @pyqtSlot("QModelIndex")
    def _treeItemDoubleClicked(self, index: QModelIndex) -> None:
        """Emit follow tag signal on user double click."""
        tHandle = index.siblingAtColumn(self.C_DATA).data(self.D_HANDLE)
        if index.column() not in (self.C_EDIT, self.C_VIEW):
            self._parent.openDocumentRequest.emit(tHandle, nwDocMode.VIEW, "", True)
        return

    ##
    #  Internal Functions
    ##

    def _setTreeItemValues(self, tHandle: str, sTitle: str, hItem: IndexHeading) -> None:
        """Add or update a tree item."""
        if nwItem := SHARED.project.tree[tHandle]:
            docIcon = SHARED.theme.getItemIcon(
                nwItem.itemType, nwItem.itemClass,
                nwItem.itemLayout, nwItem.mainHeading
            )
            iLevel = nwHeaders.H_LEVEL.get(hItem.level, 0) if nwItem.isDocumentLayout() else 5
            hDec = SHARED.theme.getHeaderDecorationNarrow(iLevel)

            tKey = f"{tHandle}:{sTitle}"
            trItem = self._treeMap[tKey] if tKey in self._treeMap else QTreeWidgetItem()

            trItem.setIcon(self.C_DOC, docIcon)
            trItem.setText(self.C_DOC, nwItem.itemName)
            trItem.setToolTip(self.C_DOC, nwItem.itemName)
            trItem.setIcon(self.C_EDIT, self._editIcon)
            trItem.setIcon(self.C_VIEW, self._viewIcon)
            trItem.setData(self.C_TITLE, Qt.ItemDataRole.DecorationRole, hDec)
            trItem.setText(self.C_TITLE, hItem.title)
            trItem.setToolTip(self.C_TITLE, hItem.title)
            trItem.setData(self.C_DATA, self.D_HANDLE, tHandle)

            if tKey not in self._treeMap:
                self.addTopLevelItem(trItem)
                self._treeMap[tKey] = trItem

        return

# END Class _ViewPanelBackRefs


class _ViewPanelKeyWords(QTreeWidget):

    C_DATA   = 0
    C_NAME   = 0
    C_EDIT   = 1
    C_VIEW   = 2
    C_IMPORT = 3
    C_DOC    = 4
    C_TITLE  = 5
    C_SHORT  = 6

    D_TAG = Qt.ItemDataRole.UserRole

    def __init__(self, parent: GuiDocViewerPanel, itemClass: nwItemClass) -> None:
        super().__init__(parent=parent)

        self._parent = parent
        self._class = itemClass
        self._treeMap: dict[str, QTreeWidgetItem] = {}

        iPx = SHARED.theme.baseIconSize
        cMg = CONFIG.pxInt(6)

        self.setHeaderLabels([
            self.tr("Tag"), "", "", self.tr("Importance"), self.tr("Document"),
            self.tr("Heading"), self.tr("Short Description")
        ])
        self.setIndentation(0)
        self.setIconSize(QSize(iPx, iPx))
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setExpandsOnDoubleClick(False)
        self.setDragEnabled(False)
        self.setSortingEnabled(True)
        self.sortByColumn(self.C_NAME, Qt.SortOrder.AscendingOrder)

        # Set Header Sizes
        treeHeader = self.header()
        treeHeader.setStretchLastSection(True)
        treeHeader.setMinimumSectionSize(iPx + cMg)  # See Issue #1627
        treeHeader.setSectionResizeMode(self.C_EDIT, QHeaderView.ResizeMode.Fixed)
        treeHeader.setSectionResizeMode(self.C_VIEW, QHeaderView.ResizeMode.Fixed)
        treeHeader.resizeSection(self.C_EDIT, iPx + cMg)
        treeHeader.resizeSection(self.C_VIEW, iPx + cMg)
        treeHeader.setSectionsMovable(False)

        # Cache Icons Locally
        self._classIcon = SHARED.theme.getIcon(nwLabels.CLASS_ICON[itemClass])
        self._editIcon = SHARED.theme.getIcon("edit")
        self._viewIcon = SHARED.theme.getIcon("view")

        # Signals
        self.clicked.connect(self._treeItemClicked)
        self.doubleClicked.connect(self._treeItemDoubleClicked)

        return

    def updateTheme(self) -> None:
        """Update theme elements."""
        self._classIcon = SHARED.theme.getIcon(nwLabels.CLASS_ICON[self._class])
        self._editIcon = SHARED.theme.getIcon("edit")
        self._viewIcon = SHARED.theme.getIcon("view")
        for i in range(self.topLevelItemCount()):
            if item := self.topLevelItem(i):
                item.setIcon(self.C_EDIT, self._editIcon)
                item.setIcon(self.C_VIEW, self._viewIcon)
        return

    def countEntries(self) -> int:
        """Return the number of items in the list."""
        return self.topLevelItemCount()

    def clearContent(self) -> None:
        """Clear the list."""
        self._treeMap = {}
        self.clear()
        return

    def addUpdateEntry(self, tag: str, name: str, iItem: IndexItem, hItem: IndexHeading) -> None:
        """Add a new entry, or update an existing one."""
        nwItem = iItem.item
        docIcon = SHARED.theme.getItemIcon(
            nwItem.itemType, nwItem.itemClass,
            nwItem.itemLayout, nwItem.mainHeading
        )
        impLabel, impIcon = nwItem.getImportStatus(incIcon=True)
        iLevel = nwHeaders.H_LEVEL.get(hItem.level, 0) if nwItem.isDocumentLayout() else 5
        hDec = SHARED.theme.getHeaderDecorationNarrow(iLevel)

        # This can not use a get call to the dictionary as that would create an
        # instance of the QTreeWidgetItem, which has some weird side effects
        trItem = self._treeMap[tag] if tag in self._treeMap else QTreeWidgetItem()

        trItem.setIcon(self.C_NAME, self._classIcon)
        trItem.setText(self.C_NAME, name)
        trItem.setToolTip(self.C_NAME, name)
        trItem.setIcon(self.C_EDIT, self._editIcon)
        trItem.setIcon(self.C_VIEW, self._viewIcon)
        trItem.setIcon(self.C_IMPORT, impIcon)
        trItem.setText(self.C_IMPORT, impLabel)
        trItem.setToolTip(self.C_IMPORT, impLabel)
        trItem.setIcon(self.C_DOC, docIcon)
        trItem.setText(self.C_DOC, nwItem.itemName)
        trItem.setToolTip(self.C_DOC, nwItem.itemName)
        trItem.setData(self.C_TITLE, Qt.ItemDataRole.DecorationRole, hDec)
        trItem.setText(self.C_TITLE, hItem.title)
        trItem.setToolTip(self.C_TITLE, hItem.title)
        trItem.setText(self.C_SHORT, hItem.synopsis)
        trItem.setToolTip(self.C_SHORT, hItem.synopsis)
        trItem.setData(self.C_DATA, self.D_TAG, tag)

        if tag not in self._treeMap:
            self.addTopLevelItem(trItem)
            self._treeMap[tag] = trItem

        return

    def removeEntry(self, tag: str) -> bool:
        """Remove a tag from the list."""
        if tag in self._treeMap:
            self.takeTopLevelItem(self.indexOfTopLevelItem(self._treeMap[tag]))
            self._treeMap.pop(tag, None)
            return True
        return False

    def setColumnWidths(self, widths: list[int]) -> None:
        """Set the column widths."""
        if isinstance(widths, list) and len(widths) >= 4:
            self.setColumnWidth(self.C_NAME, CONFIG.pxInt(checkInt(widths[0], 100)))
            self.setColumnWidth(self.C_IMPORT, CONFIG.pxInt(checkInt(widths[1], 100)))
            self.setColumnWidth(self.C_DOC, CONFIG.pxInt(checkInt(widths[2], 100)))
            self.setColumnWidth(self.C_TITLE, CONFIG.pxInt(checkInt(widths[3], 100)))
        return

    def getColumnWidths(self) -> list[int]:
        """Get the widths of the user-adjustable columns."""
        return [
            CONFIG.rpxInt(self.columnWidth(self.C_NAME)),
            CONFIG.rpxInt(self.columnWidth(self.C_IMPORT)),
            CONFIG.rpxInt(self.columnWidth(self.C_DOC)),
            CONFIG.rpxInt(self.columnWidth(self.C_TITLE)),
        ]

    ##
    #  Private Slots
    ##

    @pyqtSlot("QModelIndex")
    def _treeItemClicked(self, index: QModelIndex) -> None:
        """Emit follow tag signal on user click."""
        tag = index.siblingAtColumn(self.C_DATA).data(self.D_TAG)
        if index.column() == self.C_EDIT:
            self._parent.loadDocumentTagRequest.emit(tag, nwDocMode.EDIT)
        elif index.column() == self.C_VIEW:
            self._parent.loadDocumentTagRequest.emit(tag, nwDocMode.VIEW)
        return

    @pyqtSlot("QModelIndex")
    def _treeItemDoubleClicked(self, index: QModelIndex) -> None:
        """Emit follow tag signal on user double click."""
        tag = index.siblingAtColumn(self.C_DATA).data(self.D_TAG)
        if index.column() not in (self.C_EDIT, self.C_VIEW):
            self._parent.loadDocumentTagRequest.emit(tag, nwDocMode.VIEW)
        return

# END Class _ViewPanelKeyWords
