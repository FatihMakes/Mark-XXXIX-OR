// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T

T.Action {
    text: qsTr("Copy")
    icon.name: "edit-copy"
    icon.width: 24
    icon.height: 24
    shortcut: StandardKey.Copy
    enabled: editor.selectedText.length > 0 && editor.hasOwnProperty("copy")
    onTriggered: editor.copy()

    required property Item editor
}
