// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.NativeStyle as NativeStyle

T.RadioDelegate {
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
        readonly property bool __ignoreNotCustomizable: true
    }

    indicator: NativeStyle.RadioDelegate {
        x: control.text
           ? (control.mirrored ? control.leftPadding : control.width - width - control.rightPadding)
           : control.leftPadding + (control.availableWidth - width) / 2
        y: control.topPadding + Math.round((control.availableHeight - height) / 2)
        contentWidth: control.implicitContentWidth
        contentHeight: control.implicitContentHeight
        useNinePatchImage: false
        control: control

        readonly property bool __ignoreNotCustomizable: true
    }

    background: Rectangle {
        implicitWidth: 100
        implicitHeight: 20
        color: Qt.darker(control.highlighted
            ? control.palette.highlight : control.palette.button, control.down ? 1.05 : 1)

        readonly property bool __ignoreNotCustomizable: true
    }
}
