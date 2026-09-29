// Copyright (C) 2020 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Templates as T
import QtQuick.NativeStyle as NativeStyle

T.Button {
    id: control

    readonly property bool __nativeBackground: background instanceof NativeStyle.StyleItem
    readonly property bool __notCustomizable: true

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: __nativeBackground ? background.contentPadding.left : 5
    rightPadding: __nativeBackground ? background.contentPadding.right : 5
    topPadding: __nativeBackground ? background.contentPadding.top : 5
    bottomPadding: __nativeBackground ? background.contentPadding.bottom : 5

    background: NativeStyle.Button {
        control: control
        contentWidth: contentItem.implicitWidth
        contentHeight: contentItem.implicitHeight

        readonly property bool __ignoreNotCustomizable: true
    }

    spacing: 6

    icon.width: 24
    icon.height: 24

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
    }
}
