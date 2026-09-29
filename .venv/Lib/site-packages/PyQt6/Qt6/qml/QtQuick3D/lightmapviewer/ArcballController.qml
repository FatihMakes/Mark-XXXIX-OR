// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0
import QtQuick
import QtQuick3D

// The rotation math is based on the paper
// ARCBALL:
// A User Interface for Specifying Three-Dimensional Orientation Using a Mouse
// by Ken Shoemake, 1992
Item {
    id: root
    visible: false

    required property Node controlledObject
    property vector3d lastPos: Qt.vector3d(0, 0, 0)
    property bool moving: false

    // From Shoemake 1992:
    // pt.x <- (screen.x - center.x)/radius;
    // pt.y <- (screen.y - center.y)/radius;
    // r <- pt.x*pt.x + pt.y*pt.y;
    // IF r > 1.0
    //   THEN s <- 1.0/Sqrt[r];
    //     pt.x <- s*pt.x;
    //     pt.y <- s*pt.y;
    //     pt.z <- 0.0;
    //   ELSE pt.z <- Sqrt[1.0 - r] ;
    function pos2DToPos3D(posNDC) {
        var pt = Qt.vector3d(posNDC.x, posNDC.y, 0)
        let r = posNDC.x * posNDC.x + posNDC.y * posNDC.y
        if (r > 1.0) {
            let s = 1.0 / Math.sqrt(r)
            pt.x = s * pt.x
            pt.y = s * pt.y
            pt.z = 0.0
        } else {
            pt.z = Math.sqrt(1.0 - r)
        }

        return pt
    }

    function mousePressed(posNDC) {
        lastPos = pos2DToPos3D(posNDC)
        moving = true
    }

    function mouseReleased(posNDC) {
        moving = false
    }

    function mouseMoved(posNDC) {
        if (!moving)
            return

        let currentPos = pos2DToPos3D(posNDC)

        // From Shoemake 1992:
        // [q.x, q.y, q.z] <- V3_Cross[pO, p1];
        // q.w <- V3_Dot[pO, p1];
        // qnow <- QuatMul[q, qstart];
        let p0 = lastPos
        let p1 = currentPos
        let p0p1 = p0.crossProduct(p1)
        let q = Qt.quaternion(p0.dotProduct(p1), p0p1.x, p0p1.y, p0p1.z)
        let qnow = q.times(controlledObject.rotation)
        controlledObject.rotation = qnow
        lastPos = currentPos
    }
}
