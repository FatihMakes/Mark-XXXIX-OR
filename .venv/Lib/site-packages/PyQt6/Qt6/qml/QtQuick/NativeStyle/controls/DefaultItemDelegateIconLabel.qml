// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick.Controls.impl
import QtQuick.Templates as T

IconLabel {
    text: control.text
    font: control.font
    icon: control.icon
    color: control.palette.windowText
    spacing: control.spacing
    mirrored: control.mirrored
    display: control.display
    alignment: control.display === IconLabel.IconOnly || control.display === IconLabel.TextUnderIcon
        ? Qt.AlignCenter : Qt.AlignLeft
    leftPadding: control.indicator && control.mirrored ? control.indicator.width + control.spacing : 0
    rightPadding: control.indicator && !control.mirrored ? control.indicator.width + control.spacing : 0

    readonly property T.ItemDelegate control: parent as T.ItemDelegate
}
