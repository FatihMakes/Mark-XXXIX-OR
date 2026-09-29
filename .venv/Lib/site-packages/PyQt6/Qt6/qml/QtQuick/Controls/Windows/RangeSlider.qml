// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Templates as T

T.RangeSlider {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
        Math.max(first.implicitHandleWidth, second.implicitHandleWidth) + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
        Math.max(first.implicitHandleHeight, second.implicitHandleHeight) + topPadding + bottomPadding)

    readonly property bool __notCustomizable: true
    readonly property Item __focusFrameTarget: control

    component SliderHandle: Rectangle {
        implicitWidth: control.horizontal ? 11 : 21
        implicitHeight: control.horizontal ? 21 : 11
        color: control.palette.highlight

        required property bool pressed
    }

    first.handle: SliderHandle {
        x: control.leftPadding + Math.round(control.horizontal
            ? control.first.visualPosition * (control.availableWidth - width)
            : (control.availableWidth - width) / 2)
        y: control.topPadding + Math.round(control.horizontal
            ? (control.availableHeight - height) / 2
            : control.first.visualPosition * (control.availableHeight - height))
        palette: control.palette
        pressed: control.first.pressed

        // We are the ones that get focus, but we want the control to
        // be used for the visual focus frame.
        readonly property Item __focusFrameControl: control
        readonly property bool __ignoreNotCustomizable: true
    }

    second.handle: SliderHandle {
        x: control.leftPadding + Math.round(control.horizontal
            ? control.second.visualPosition * (control.availableWidth - width)
            : (control.availableWidth - width) / 2)
        y: control.topPadding + Math.round(control.horizontal
            ? (control.availableHeight - height) / 2
            : control.second.visualPosition * (control.availableHeight - height))
        palette: control.palette
        pressed: control.second.pressed

        readonly property Item __focusFrameControl: control
        readonly property bool __ignoreNotCustomizable: true
    }

    background: Item {
        implicitWidth: control.horizontal ? 90 : 21
        implicitHeight: control.horizontal ? 21 : 90

        readonly property real __focusFrameRadius: 1
        readonly property bool __ignoreNotCustomizable: true
        readonly property int barThickness: 4

        // Groove background.
        Rectangle {
            x: control.leftPadding + (control.horizontal ? 0 : (control.availableWidth - width) / 2)
            y: control.topPadding + (control.horizontal ? (control.availableHeight - height) / 2 : 0)
            width: control.horizontal ? control.availableWidth : parent.barThickness
            height: control.horizontal ? parent.barThickness : control.availableHeight
            color: control.palette.window

            Rectangle {
                width: parent.width
                height: parent.height
                radius: parent.radius
                // No border in dark mode, instead we fill.
                color: Application.styleHints.colorScheme === Qt.Light
                    ? "transparent" : Qt.lighter(control.palette.window, 1.6)
                border.color: Application.styleHints.colorScheme === Qt.Light
                    ? Qt.darker(control.palette.window, 1.1)
                    : "transparent"
            }
        }

        // Progress bar.
        Rectangle {
            x: control.leftPadding + (control.horizontal
                ? control.first.position * control.availableWidth
                : (control.availableWidth - width) / 2)
            y: control.topPadding + (control.horizontal
                ? (control.availableHeight - height) / 2
                : control.second.visualPosition * control.availableHeight)

            width: control.horizontal
                ? control.second.position * control.availableWidth - control.first.position * control.availableWidth
                : parent.barThickness
            height: control.horizontal
                ? parent.barThickness
                : control.second.position * control.availableHeight - control.first.position * control.availableHeight
            color: Qt.rgba(control.palette.highlight.r, control.palette.highlight.g, control.palette.highlight.b, 0.3)
        }
    }
}
