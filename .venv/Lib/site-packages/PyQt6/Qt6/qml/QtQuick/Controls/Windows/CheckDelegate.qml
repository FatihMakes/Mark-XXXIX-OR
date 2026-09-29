// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.NativeStyle as NativeStyle

T.CheckDelegate {
    id: control

    readonly property bool __nativeIndicator: indicator instanceof NativeStyle.StyleItem
    readonly property bool __notCustomizable: true
    readonly property Item __focusFrameTarget: indicator
    readonly property Item __focusFrameStyleItem: indicator

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)

    spacing: 6
    padding: 6

    icon.width: 16
    icon.height: 16

    contentItem: NativeStyle.DefaultItemDelegateIconLabel {
        color: control.highlighted ? control.palette.button : control.palette.windowText

        readonly property bool __ignoreNotCustomizable: true
    }

    indicator: NativeStyle.CheckDelegate {
        x: control.text
           ? (control.mirrored ? control.leftPadding : control.width - width - control.rightPadding)
           : control.leftPadding + (control.availableWidth - width) / 2
        // The rendering gets messed up when rendering on sub-pixel positions.
        y: control.topPadding + Math.round((control.availableHeight - height) / 2)
        contentWidth: control.implicitContentWidth
        contentHeight: control.implicitContentHeight
        control: control
        useNinePatchImage: false
        overrideState: NativeStyle.StyleItem.NeverHovered

        readonly property bool __ignoreNotCustomizable: true
    }

    NativeStyle.CheckDelegate {
        id: hoverCheckDelegate
        control: control
        x: control.indicator.x
        y: control.indicator.y
        z: control.indicator.z + 1
        width: control.indicator.width
        height: control.indicator.height
        useNinePatchImage: false
        overrideState: NativeStyle.StyleItem.AlwaysHovered
        opacity: control.hovered ? 1 : 0
        visible: opacity !== 0
        Behavior on opacity {
            NumberAnimation {
                duration: hoverCheckDelegate.transitionDuration
            }
        }
    }

    background: Rectangle {
        implicitWidth: 100
        implicitHeight: 20
        color: Qt.darker(control.highlighted
            ? control.palette.highlight : control.palette.button, control.down ? 1.05 : 1)

        readonly property bool __ignoreNotCustomizable: true
    }
}
