// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.Universal
import QtQuick.Controls.Universal.impl as UniversalImpl

Menu {
    id: menu
    popupType: Qt.platform.pluginName !== "wayland" ? Popup.Window : Popup.Item

    required property Item editor

    UniversalImpl.UndoAction {
        editor: menu.editor
    }
    UniversalImpl.RedoAction {
        editor: menu.editor
    }

    MenuSeparator {}

    UniversalImpl.CutAction {
        editor: menu.editor
    }
    UniversalImpl.CopyAction {
        editor: menu.editor
    }
    UniversalImpl.PasteAction {
        editor: menu.editor
    }
    UniversalImpl.DeleteAction {
        editor: menu.editor
    }

    MenuSeparator {}

    UniversalImpl.SelectAllAction {
        editor: menu.editor
    }
}
