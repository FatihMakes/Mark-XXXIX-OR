// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Controls.Fusion
import QtQuick.Controls.Fusion.impl as FusionImpl

Menu {
    id: menu
    popupType: Qt.platform.pluginName !== "wayland" ? Popup.Window : Popup.Item

    required property Item editor

    FusionImpl.UndoAction {
        editor: menu.editor
    }
    FusionImpl.RedoAction {
        editor: menu.editor
    }

    MenuSeparator {}

    FusionImpl.CutAction {
        editor: menu.editor
    }
    FusionImpl.CopyAction {
        editor: menu.editor
    }
    FusionImpl.PasteAction {
        editor: menu.editor
    }
    FusionImpl.DeleteAction {
        editor: menu.editor
    }

    MenuSeparator {}

    FusionImpl.SelectAllAction {
        editor: menu.editor
    }
}
