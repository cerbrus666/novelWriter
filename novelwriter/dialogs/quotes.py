"""
novelWriter – GUI Quotes Dialog
===============================

File History:
Created: 2020-06-18 [0.9.0] GuiQuoteSelect

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

from PyQt5.QtGui import QCloseEvent, QFontMetrics
from PyQt5.QtCore import QSize, Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QVBoxLayout, QWidget
)

from novelwriter import CONFIG
from novelwriter.constants import trConst, nwQuotes

logger = logging.getLogger(__name__)


class GuiQuoteSelect(QDialog):

    selectedQuote = ""

    D_KEY = Qt.ItemDataRole.UserRole

    def __init__(self, parent: QWidget, currentQuote: str = '"') -> None:
        super().__init__(parent=parent)

        logger.debug("Create: GuiQuoteSelect")
        self.setObjectName("GuiQuoteSelect")

        self.outerBox = QVBoxLayout()
        self.innerBox = QHBoxLayout()
        self.labelBox = QVBoxLayout()

        self.selectedQuote = currentQuote

        qMetrics = QFontMetrics(self.font())
        pxW = 7*qMetrics.boundingRectChar("M").width()
        pxH = 7*qMetrics.boundingRectChar("M").height()
        pxH = 7*qMetrics.boundingRectChar("M").height()

        lblFont = self.font()
        lblFont.setPointSizeF(4*lblFont.pointSizeF())

        # Preview Label
        self.previewLabel = QLabel(currentQuote)
        self.previewLabel.setFont(lblFont)
        self.previewLabel.setFixedSize(QSize(pxW, pxH))
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setFrameStyle(QFrame.Box | QFrame.Plain)

        # Quote Symbols
        self.listBox = QListWidget()
        self.listBox.itemSelectionChanged.connect(self._selectedSymbol)

        minSize = 100
        for sKey, sLabel in nwQuotes.SYMBOLS.items():
            theText = "[ %s ] %s" % (sKey, trConst(sLabel))
            minSize = max(minSize, qMetrics.boundingRect(theText).width())
            qtItem = QListWidgetItem(theText)
            qtItem.setData(self.D_KEY, sKey)
            self.listBox.addItem(qtItem)
            if sKey == currentQuote:
                self.listBox.setCurrentItem(qtItem)

        self.listBox.setMinimumWidth(minSize + CONFIG.pxInt(40))
        self.listBox.setMinimumHeight(CONFIG.pxInt(150))

        # Buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Assemble
        self.labelBox.addWidget(self.previewLabel, 0, Qt.AlignTop)
        self.labelBox.addStretch(1)

        self.innerBox.addLayout(self.labelBox)
        self.innerBox.addWidget(self.listBox)

        self.outerBox.addLayout(self.innerBox)
        self.outerBox.addWidget(self.buttonBox)

        self.setLayout(self.outerBox)

        logger.debug("Ready: GuiQuoteSelect")

        return

    def __del__(self) -> None:  # pragma: no cover
        logger.debug("Delete: GuiQuoteSelect")
        return

    ##
    #  Events
    ##

    def closeEvent(self, event: QCloseEvent) -> None:
        """Capture the close event and perform cleanup."""
        event.accept()
        self.deleteLater()
        return

    ##
    #  Private Slots
    ##

    @pyqtSlot()
    def _selectedSymbol(self) -> None:
        """Update the preview label and the selected quote style."""
        selItems = self.listBox.selectedItems()
        if selItems:
            theSymbol = selItems[0].data(self.D_KEY)
            self.previewLabel.setText(theSymbol)
            self.selectedQuote = theSymbol
        return

# END Class GuiQuoteSelect
