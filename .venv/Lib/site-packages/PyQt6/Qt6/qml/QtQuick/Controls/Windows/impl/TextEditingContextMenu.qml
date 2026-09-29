// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick.Controls.Windows
import QtQuick.Controls.Windows.impl as WindowsImpl

Menu {
    id: menu
    popupType: Popup.Window

    required property var editor

    WindowsImpl.UndoAction {
        editor: menu.editor
    }
    WindowsImpl.RedoAction {
        editor: menu.editor
    }

    MenuSeparator {}

    WindowsImpl.CutAction {
        editor: menu.editor
    }
    WindowsImpl.CopyAction {
        editor: menu.editor
    }
    WindowsImpl.PasteAction {
        editor: menu.editor
    }
    WindowsImpl.DeleteAction {
        editor: menu.editor
    }

    MenuSeparator {}

    WindowsImpl.SelectAllAction {
        editor: menu.editor
    }
}
