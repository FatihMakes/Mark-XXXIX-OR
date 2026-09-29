// Copyright (C) 2023 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick

Canvas {
    id: root
    x: targetItem ? targetItem.x + leftOffset - frameSize : 0
    y: targetItem ? targetItem.y + topOffset - frameSize : 0
    // Stack on top of all siblings of the targetItem
    z: 100
    width: targetItem ? targetItem.width - leftOffset - rightOffset + (frameSize * 2) : 0
    height: targetItem ? targetItem.height - topOffset - bottomOffset + (frameSize * 2) : 0
    visible: targetItem && targetItem.visible

    function moveToItem(item, margins, radius) {
        if (!item) {
            targetItem = null;
            parent = null;
            return;
        }
        parent = item.parent
        targetItem = item
        leftOffset = margins.left
        rightOffset = margins.right
        topOffset = margins.top
        bottomOffset = margins.bottom
        frameRadius = radius
    }

    property Item targetItem
    property real leftOffset: 0
    property real rightOffset: 0
    property real topOffset: 0
    property real bottomOffset: 0
    property real frameOpacity: 0
    property real frameSize: 0
    property real frameRadius: 0

    onPaint: {
        let context = getContext("2d")
        context.strokeStyle = Qt.rgba(0, 0, 0, 1)
        context.setLineDash([1, 1])
        context.beginPath()
        context.roundedRect(0.5, 0.5, width - 1, height - 1, root.frameRadius, root.frameRadius)
        context.stroke()
    }
}
