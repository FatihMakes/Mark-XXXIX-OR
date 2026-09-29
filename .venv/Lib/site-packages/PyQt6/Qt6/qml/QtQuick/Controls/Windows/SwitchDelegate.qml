// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Windows.impl
import QtQuick.NativeStyle as NativeStyle

T.SwitchDelegate {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)

    padding: 6
    spacing: 6

    icon.width: 16
    icon.height: 16

    readonly property bool __notCustomizable: true
    readonly property Item __focusFrameTarget: indicator
    readonly property Item __focusFrameStyleItem: indicator

    indicator: SwitchIndicator {
        x: control.text
           ? (control.mirrored ? control.leftPadding : control.width - width - control.rightPadding)
           : control.leftPadding + (control.availableWidth - width) / 2
    }

    contentItem: NativeStyle.DefaultItemDelegateIconLabel {
        color: control.highlighted ? control.palette.button : control.palette.windowText

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
