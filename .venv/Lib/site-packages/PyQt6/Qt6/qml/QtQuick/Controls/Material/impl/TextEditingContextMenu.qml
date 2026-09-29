// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.impl
import QtQuick.Controls.Material

Menu {
    id: menu
    popupType: Qt.platform.pluginName !== "wayland" ? Popup.Window : Popup.Item

    required property Item editor

    UndoAction {
        editor: menu.editor
    }
    RedoAction {
        editor: menu.editor
    }

    MenuSeparator {}

    CutAction {
        editor: menu.editor
    }
    CopyAction {
        editor: menu.editor
    }
    PasteAction {
        editor: menu.editor
    }
    DeleteAction {
        editor: menu.editor
    }

    MenuSeparator {}

    SelectAllAction {
        editor: menu.editor
    }
}
