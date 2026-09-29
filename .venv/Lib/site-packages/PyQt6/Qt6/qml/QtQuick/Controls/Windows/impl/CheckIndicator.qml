// Copyright (C) 2024 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.impl

Item {
    id: indicator
    implicitWidth: 14
    implicitHeight: 10

    property Item control

    ColorImage {
        y: (parent.height - height) / 2
        color: control.palette.text
        source: "qrc:/qt-project.org/imports/QtQuick/Controls/Windows/images/checkmark.png"
        visible: indicator.control.checkState === Qt.Checked
                 || (indicator.control.checked && indicator.control.checkState === undefined)
    }
}
