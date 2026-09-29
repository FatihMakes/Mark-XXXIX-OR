// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.impl
import QtQuick.Templates as T

Rectangle {
    required property T.Control control

    implicitWidth: 100
    implicitHeight: 40
    visible: control.down || control.highlighted || control.visualFocus
    color: Color.blend(control.down ? control.palette.midlight : control.palette.light,
                                      control.palette.highlight, control.highlighted ? 0.15 : 0.0)
}
