// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.impl
import QtQuick.Templates as T
import QtQuick.NativeStyle as NativeStyle

T.DelayButton {
    id: control

    readonly property bool __nativeBackground: background instanceof NativeStyle.StyleItem
    readonly property bool __notCustomizable: true
    readonly property Item __focusFrameTarget: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: __nativeBackground ? background.contentPadding.left : 5
    rightPadding: __nativeBackground ? background.contentPadding.right : 5
    topPadding: __nativeBackground ? background.contentPadding.top : 5
    bottomPadding: __nativeBackground ? background.contentPadding.bottom : 5

    icon.width: 24
    icon.height: 24

    transition: Transition {
        NumberAnimation {
            duration: control.delay * (control.pressed ? 1.0 - control.progress : 0.3 * control.progress)
        }
    }

    background: NativeStyle.DelayButton {
        control: control
        contentWidth: contentItem.implicitWidth
        contentHeight: contentItem.implicitHeight
        useNinePatchImage: false
        overrideState: NativeStyle.StyleItem.NeverHovered

        readonly property bool __ignoreNotCustomizable: true
    }

    NativeStyle.DelayButton {
        id: hoverButton
        control: control
        x: background.x
        y: background.y
        width: background.width
        height: background.height
        useNinePatchImage: false
        overrideState: NativeStyle.StyleItem.AlwaysHovered
        opacity: control.hovered ? 1 : 0
        visible: opacity !== 0
        Behavior on opacity { NumberAnimation { duration: hoverButton.transitionDuration } }
    }

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display

        icon: control.icon
        defaultIconColor: control.palette.buttonText
        text: control.text
        font: control.font
        color: defaultIconColor

        readonly property bool __ignoreNotCustomizable: true

        // Delay progress bar.
        Rectangle {
            x: (parent.width - parent.implicitWidth) / 2
            y: parent.height + 1
            width: control.progress * parent.implicitWidth
            height: 1
            color: control.palette.accent
            scale: control.mirrored ? -1 : 1
        }
    }
}
