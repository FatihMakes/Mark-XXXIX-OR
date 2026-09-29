// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T

Rectangle {
    id: root
    x: control.text ? (control.mirrored
                       ? control.width - width - control.rightPadding : control.leftPadding)
                    : control.leftPadding + (control.availableWidth - width) / 2
    y: control.topPadding + (control.availableHeight - height) / 2
    implicitWidth: 40
    implicitHeight: 16
    radius: 3
    color: Qt.darker(control.palette.button, control.down ? 1.2 : 1.1)
    border.color: Qt.darker(control.palette.window, 1.4)

    readonly property bool __ignoreNotCustomizable: true
    readonly property real __focusFrameRadius: 2
    readonly property T.AbstractButton control: parent as T.AbstractButton

    // Checked indicator.
    Rectangle {
        x: root.control.mirrored ? parent.children[1].x : 0
        width: root.control.mirrored
            ? parent.width - parent.children[1].x : parent.children[1].x + parent.children[1].width
        height: parent.height
        radius: 3
        color: Qt.darker(root.control.palette.highlight, root.control.down ? 1.1 : 1)
        border.color: Qt.darker(root.control.palette.highlight, 1.35)
        border.width: root.control.enabled ? 1 : 0
        opacity: root.control.checked ? 1 : 0

        Behavior on opacity {
            enabled: !root.control.down
            NumberAnimation { duration: 80 }
        }
    }

    // Handle.
    Rectangle {
        x: Math.max(0, Math.min(parent.width - width,
            root.control.visualPosition * parent.width - (width / 2)))
        y: (parent.height - height) / 2
        width: 20
        height: 16
        radius: 3
        color: Qt.lighter(root.control.palette.button, root.control.down
            ? 1 : (root.control.hovered ? 1.07 : 1.045))
        border.width: 1
        border.color: Qt.darker(root.control.palette.window, 1.4)

        Behavior on x {
            enabled: !root.control.down
            SmoothedAnimation { velocity: 200 }
        }
    }
}
