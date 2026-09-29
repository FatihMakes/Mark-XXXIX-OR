// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T

T.Action {
    text: qsTr("Delete")
    icon.name: "edit-delete"
    icon.width: 24
    icon.height: 24
    shortcut: StandardKey.Delete
    enabled: !editor.readOnly && editor.selectedText.length > 0
    onTriggered: editor.remove(editor.selectionStart, editor.selectionEnd)

    required property Item editor
}
