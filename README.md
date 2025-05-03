# Kreed Utility

A Blender add-on for managing vertex groups, UVs, and mesh optimization. Compatible with Blender 3.6.11 and 4.x.

## Overview

Kreed Utility provides a comprehensive set of tools for mesh optimization, especially focused on game engine compatibility (specifically RE Engine and RE4 OG). The add-on provides utilities for:

- Vertex group management
- UV map optimization
- Normal management
- Mesh cleanup and optimization

![picture](https://i.imgur.com/ojQf8pp.png)

## Installation

1. Download the latest release (as a ZIP file)
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install" and select the downloaded ZIP file
4. Enable the add-on by checking the box next to "Mesh: Kreed Utility"

## Features

### Mesh Information Panel

- Shows current mesh statistics (vertex/face count)
- Displays UV map information
- Indicates mesh optimization status
- Provides toggle for face orientation display

### Vertex Group Management

- **Mix Vertex Weights**: Transfer weights from one vertex group to another
- **Remove Empty Vertex Groups**: Cleans all empty vertex groups from all mesh objects in the scene
- **Sort Vertex Groups**: Alphabetically sorts vertex groups
- **Weight Condenser**: Normalizes weights, limiting to 8 per vertex with 0.02 threshold

### UV Tools

- **Solve Repeated UVs**: Fixes overlapping UVs by splitting UV islands while preserving normals

### Normals Management

- **Weighted Normals**: Applies weighted normals with default settings
- Cross-version compatibility for auto smoothing (Blender 3.x and 4.x)

### Mesh Cleanup

- **Cleanup Mesh**: Full mesh optimization (removes loose geometry, dissolves degenerate edges, merges by distance, applies weighted normals)
- **Merge & Weighted Normal**: Merges vertices by distance and applies weighted normals

## Tool Descriptions

### Mix Vertex Weights

Transfers weights from a source vertex group to a target group. Useful for combining bone influences or creating composite deformations.

### Remove Empty Vertex Groups

Scans all mesh objects in the scene and removes any vertex groups that don't have any weights assigned. This helps clean up your meshes and reduce file size.

### Weight Condenser

Performs a complete vertex weight optimization:
1. Limits weights to 8 per vertex (game engine compatibility)
2. Cleans weights below 0.02 threshold
3. Removes empty groups
4. Normalizes all remaining weights

### Solve Repeated UVs

Fixes meshes with overlapping UVs by:
1. Detecting vertices with multiple UV coordinates
2. Splitting the mesh along UV islands
3. Preserving vertex normals during the process
4. Marks the mesh as "RE Engine Optimized"

### Merge & Weighted Normal

Standard mesh optimization for RE4 OG:
1. Merges vertices that are closer than 0.0001 units
2. Applies weighted normals for smooth shading
3. Marks the mesh as "RE4 OG Optimized"

### Cleanup Mesh

Comprehensive mesh cleanup:
1. Deletes loose geometry (vertices, edges)
2. Dissolves degenerate edges/faces
3. Merges vertices by distance
4. Applies weighted normals

## Compatibility

- Blender 3.6.11
- Tested on Blender 4.1