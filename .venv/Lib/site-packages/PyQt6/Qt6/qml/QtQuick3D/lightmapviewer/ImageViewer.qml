// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0
import QtQuick

import LightmapFile 1.0

Rectangle {
    id: scrollView
    clip: true
    color: "black"

    property real lastMouseX: 0
    property real lastMouseY: 0

    function clamp() {
        // If the image is smaller than the scroll view, center it
        if (image.width <= scrollView.width) {
            imageCenterX = 0
        } else {
            const maxOffsetX = (image.width - scrollView.width) / 2
            imageCenterX = Math.max(-maxOffsetX,
                                    Math.min(imageCenterX,
                                             maxOffsetX))
        }

        if (image.height <= scrollView.height) {
            imageCenterY = 0
        } else {
            const maxOffsetY = (image.height - scrollView.height) / 2
            imageCenterY = Math.max(-maxOffsetY,
                                    Math.min(imageCenterY,
                                             maxOffsetY))
        }
    }

    onWidthChanged: clamp()
    onHeightChanged: clamp()

    Connections {
        target: window
        function onSelectedEntryChanged() {
            if (imageLoader.item === scrollView) {
                imageZoom = 1
                imageCenterX = 0
                imageCenterY = 0
            }
        }
    }

    MouseArea {
        id: mouseArea
        property bool dragging: false
        anchors.fill: parent
        onPressed: mouse => {
                       scrollView.lastMouseX = mouse.x
                       scrollView.lastMouseY = mouse.y
                       dragging = true
                   }
        onReleased: mouse => {
                        dragging = false
                    }

        onPositionChanged: mouse => {
                               var dx = mouse.x - scrollView.lastMouseX
                               var dy = mouse.y - scrollView.lastMouseY

                               scrollView.lastMouseX = mouse.x
                               scrollView.lastMouseY = mouse.y

                               imageCenterX += dx
                               imageCenterY += dy

                               clamp()
                           }
        cursorShape: mouseArea.dragging ? Qt.ClosedHandCursor : Qt.ArrowCursor

        onWheel: event => {
                     const oldZoom = imageZoom
                     const zoomDelta = event.angleDelta.y / 256
                     const newZoom = Math.max(
                         1, Math.min(32, oldZoom + zoomDelta))

                     if (newZoom === oldZoom)
                     return

                     // Adjust center offset so the same point remains at the center
                     const scaleFactor = newZoom / oldZoom
                     imageCenterX *= scaleFactor
                     imageCenterY *= scaleFactor

                     imageZoom = newZoom
                     clamp()

                     event.accepted = true
                 }
    }

    Image {
        id: baseGrid
        anchors.fill: scrollView
        source: "grid.png"
        fillMode: Image.Tile
        opacity: 0.75
    }

    Rectangle {
        width: image.width + (border.width * 2)
        height: image.height + (border.width * 2)
        x: image.x - border.width
        y: image.y - border.width
        color: "white" // This is the border color

        border.width: 0
        border.color: "white"
        opacity: 0.25
        visible: window.isImage(window.selectedEntry)
    }

    Image {
        id: image
        x: Math.round(parent.width / 2 - width / 2) + imageCenterX
        y: Math.round(parent.height / 2 - height / 2) + imageCenterY
        source: window.isImage(
                    window.selectedEntry) ? `image://lightmaps/key=${selectedEntry.key}&tag=${selectedEntry.tag}&file=${LightmapFile.source}&alpha=${alphaSwitch.checked}` : ""
        onWidthChanged: clamp()
        onHeightChanged: clamp()
        fillMode: Image.PreserveAspectFit
        smooth: false
        antialiasing: false

        // Let the image scale visibly
        width: sourceSize.width * imageZoom
        height: sourceSize.height * imageZoom
    }
}
