// Copyright (C) 2024 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Window
import QtQuick.Effects

T.Menu {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    // The insets are found by examining the MultiEffect.itemRect, which
    // contains the drop shadow offsets. Note: the insets are hard-coded
    // to avoid a binding loop to implicit size.
    leftInset: -32
    topInset: -32
    rightInset: -32
    bottomInset: -32
    leftPadding: 5
    topPadding: 5
    rightPadding: 5
    bottomPadding: 5
    margins: 0
    overlap: 4

    delegate: MenuItem { }

    contentItem: ListView {
        implicitHeight: contentHeight
        model: control.contentModel
        interactive: Window.window
                     ? contentHeight + control.topPadding + control.bottomPadding > control.height
                     : false
        currentIndex: control.currentIndex
        spacing: 2

        ScrollIndicator.vertical: ScrollIndicator {}
    }

    background: Item {
        implicitWidth: 200 - control.leftInset - control.rightInset
        implicitHeight: 20 - control.topInset - control.bottomInset
        MultiEffect {
            x: -control.leftInset
            y: -control.topInset
            width: source.width
            height: source.height
            source: Rectangle {
                width: control.background.width + control.leftInset + control.rightInset
                height: control.background.height + control.topInset + control.bottomInset
                radius: 8
                color: Qt.lighter(control.palette.window, 1.15)
                border.color: Qt.darker(control.palette.window, 1.12)
                visible: false
            }
            shadowScale: 1.04
            shadowOpacity: 0.1
            shadowColor: 'black'
            shadowEnabled: true
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 6
        }
    }

    T.Overlay.modal: Rectangle {
        color: "transparent"
    }

    T.Overlay.modeless: Rectangle {
        color: "transparent"
    }
}
