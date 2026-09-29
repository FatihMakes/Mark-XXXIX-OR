// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.FluentWinUI3
import QtQuick.Controls.FluentWinUI3.impl as FluentWinUI3Impl

Menu {
    id: menu
    popupType: Qt.platform.pluginName !== "wayland" ? Popup.Window : Popup.Item

    required property Item editor

    FluentWinUI3Impl.UndoAction {
        editor: menu.editor
    }
    FluentWinUI3Impl.RedoAction {
        editor: menu.editor
    }

    MenuSeparator {}

    FluentWinUI3Impl.CutAction {
        editor: menu.editor
    }
    FluentWinUI3Impl.CopyAction {
        editor: menu.editor
    }
    FluentWinUI3Impl.PasteAction {
        editor: menu.editor
    }
    FluentWinUI3Impl.DeleteAction {
        editor: menu.editor
    }

    MenuSeparator {}

    FluentWinUI3Impl.SelectAllAction {
        editor: menu.editor
    }
}
