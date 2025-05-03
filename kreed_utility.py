bl_info = {
    "name": "Kreed Utility",
    "author": "kreed",
    "version": (1, 1),
    "blender": (3, 6, 11),
    "location": "View3D > Sidebar > Kreed Utility",
    "description": "Tools for managing vertex groups, UVs and mesh optimization (Compatible with Blender 3.6.11 and 4.x)",
    "category": "Mesh",
}

import bpy
from bpy.types import Panel, Operator
import bmesh
from mathutils import Vector

bpy.types.Object.kreed_re_engine_optimized = bpy.props.BoolProperty(
    name="RE Engine Optimized",
    description="Indicates if the mesh has been optimized for RE Engine",
    default=False
)

bpy.types.Object.kreed_re4_og_optimized = bpy.props.BoolProperty(
    name="RE4 OG Optimized",
    description="Indicates if the mesh has been optimized for RE4 OG",
    default=False
)

def set_auto_smooth(obj, enable=True, angle=0.523599):
    """
    Set auto smooth settings in a version-compatible way
    """
    if bpy.app.version < (4, 0, 0):
        obj.data.use_auto_smooth = enable
        obj.data.auto_smooth_angle = angle
    else:
        # In Blender 4.x+, we just use shade smooth with custom normals
        if enable:
            # Ensure we're in object mode
            if bpy.context.active_object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Apply smooth shading
            bpy.ops.object.shade_smooth()
            
            # Add custom split normals if they don't exist
            bpy.ops.mesh.customdata_custom_splitnormals_add()
            
            # Set faces to smooth
            for poly in obj.data.polygons:
                poly.use_smooth = True

class OBJECT_OT_mix_vertex_weights(Operator):
    bl_idname = "object.mix_vertex_weights"
    bl_label = "Mix Vertex Weights"
    bl_description = "Mix vertex weights within the same object"
    
    group_a: bpy.props.StringProperty(
        name="Target Group",
        description="Vertex group that will receive the weights"
    )
    
    group_b: bpy.props.StringProperty(
        name="Source Group",
        description="Vertex group that will be added"
    )
    
    remove_source_group: bpy.props.BoolProperty(
        name="Remove Source Group",
        description="Remove the source vertex group after mixing",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        # Only allow for a single mesh object
        return (context.active_object and 
                context.active_object.type == 'MESH' and 
                len(context.active_object.vertex_groups) > 1)
    
    def invoke(self, context, event):
        # Pre-select active vertex groups if they exist
        obj = context.active_object
        
        if obj.vertex_groups.active:
            self.group_a = obj.vertex_groups.active.name
        
        # Open a props dialog to select the second group and confirm removal
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        # Target (Group A) selection
        box = layout.box()
        box.label(text="Target Vertex Group:", icon='OBJECT_DATA')
        box.prop_search(self, "group_a", obj, "vertex_groups", text="Target Group")
        
        # Source (Group B) selection
        box = layout.box()
        box.label(text="Source Vertex Group:", icon='OBJECT_DATA')
        box.prop_search(self, "group_b", obj, "vertex_groups", text="Source Group")
        
        # Remove source group option
        layout.prop(self, "remove_source_group")
    
    def execute(self, context):
        try:
            obj = context.active_object
            
            if not self.group_a or not self.group_b:
                self.report({'ERROR'}, "Please select both vertex groups")
                return {'CANCELLED'}
            
            # Add vertex weight mix modifier
            modifier = obj.modifiers.new(name="VertexWeightMix", type='VERTEX_WEIGHT_MIX')
            modifier.vertex_group_a = self.group_a
            modifier.vertex_group_b = self.group_b
            modifier.mix_mode = 'ADD'
            modifier.mix_set = 'ALL'
            modifier.normalize = False
            
            # Apply the modifier
            bpy.ops.object.modifier_apply(modifier="VertexWeightMix")
            
            # Remove source group if option is selected
            if self.remove_source_group:
                vgroup_to_remove = obj.vertex_groups.get(self.group_b)
                if vgroup_to_remove:
                    obj.vertex_groups.remove(vgroup_to_remove)
                
                # Sort vertex groups
                bpy.ops.object.vertex_group_sort(sort_type='NAME')
            
            # Construct success message
            message = f"Mixed weights from {self.group_b} to {self.group_a}"
            if self.remove_source_group:
                message += " and removed source group"
            
            self.report({'INFO'}, message)
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error mixing weights: {str(e)}")
            return {'CANCELLED'}

class OBJECT_OT_remove_empty_vertex_groups(Operator):
    bl_idname = "object.remove_empty_vertex_groups"
    bl_label = "Remove empty Vertex Groups"
    bl_description = "Removes all empty vertex groups from all mesh objects in the scene"
    
    @classmethod
    def poll(cls, context):
        # Allow operation if there's at least one mesh object in the scene
        return any(obj.type == 'MESH' for obj in bpy.data.objects)
    
    def is_empty_group(self, obj, vgroup):
        """Check if a vertex group has no weights"""
        is_empty = True
        for vert in obj.data.vertices:
            try:
                vgroup.weight(vert.index)
                is_empty = False
                break
            except RuntimeError:
                continue
        return is_empty
    
    def execute(self, context):
        total_removed = 0
        total_objects_affected = 0
        
        # Iterate through all mesh objects in the scene
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.vertex_groups:
                continue
                
            # Find empty groups in this object
            empty_groups = []
            for vgroup in obj.vertex_groups:
                if self.is_empty_group(obj, vgroup):
                    empty_groups.append(vgroup)
            
            # Remove the empty groups
            for vgroup in empty_groups:
                obj.vertex_groups.remove(vgroup)
            
            # Update counters
            if empty_groups:
                total_objects_affected += 1
                total_removed += len(empty_groups)
        
        # Report results
        if total_removed > 0:
            self.report({'INFO'}, f"Removed {total_removed} empty vertex groups from {total_objects_affected} objects")
        else:
            self.report({'INFO'}, "No empty vertex groups found in any objects")
            
        return {'FINISHED'}

class OBJECT_OT_sort_vertex_groups(Operator):
    bl_idname = "object.sort_vertex_groups"
    bl_label = "Sort Vertex Groups"
    bl_description = "Sort vertex groups by name"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        # Sort vertex groups by name
        bpy.ops.object.vertex_group_sort(sort_type='NAME')
        self.report({'INFO'}, "Vertex groups sorted by name")
        return {'FINISHED'}

class OBJECT_OT_normalize_weights(Operator):
    bl_idname = "object.normalize_weights"
    bl_label = "Weight Condenser"
    bl_description = "Limit weights to 8, clean with 0.02 threshold, remove empty groups and normalize all"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        # Limit total weights per vertex
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=8)
        
        # Clean weights with 0.02 threshold
        for vgroup in obj.vertex_groups:
            obj.vertex_groups.active_index = vgroup.index
            bpy.ops.object.vertex_group_clean(group_select_mode='ACTIVE', limit=0.02)
        
        # Remove empty groups
        bpy.ops.object.remove_empty_vertex_groups()
        
        # Normalize all groups
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
        
        self.report({'INFO'}, "Weights normalized")
        return {'FINISHED'}

class OBJECT_OT_solve_repeated_uvs(Operator):
    bl_idname = "object.solve_repeated_uvs"
    bl_label = "Solve Repeated UVs"
    bl_description = "Fix overlapping UVs by splitting UV islands and preserving normals"
    
    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)
    
    def clone_mesh(self, mesh):
        new_obj = mesh.copy()
        new_obj.data = mesh.data.copy()
        bpy.context.scene.collection.objects.link(new_obj)
        return new_obj

    def bad_iter(self, blender_crap):
        i = 0
        while True:
            try:
                yield(blender_crap[i])
                i += 1
            except:
                return

    def select_repeated(self, bm):
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()
        target_vert = set()
        for uv_layer in self.bad_iter(bm.loops.layers.uv):
            uv_map = {}
            for face in bm.faces:
                for loop in face.loops:
                    uv_point = tuple(loop[uv_layer].uv)
                    if loop.vert.index in uv_map and uv_map[loop.vert.index] != uv_point:
                        target_vert.add(bm.verts[loop.vert.index])
                    else:
                        uv_map[loop.vert.index] = uv_point
        return target_vert

    def solve_repeated_vertex(self, mesh):
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(mesh.data)
        old_mode = bm.select_mode
        bm.select_mode = {'VERT'}    
        targets = self.select_repeated(bm)
        for target in targets:
            bmesh.utils.vert_separate(target, target.link_edges)
            bm.verts.ensure_lookup_table()    
        bpy.ops.mesh.select_all(action='DESELECT')
        bm.select_mode = old_mode
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bmesh.update_edit_mesh(mesh.data) 
        mesh.data.update()

    def transfer_normals(self, clone, mesh):
        mod = mesh.modifiers.new("Normals Transfer", "DATA_TRANSFER")
        mod.use_loop_data = True
        mod.loop_mapping = "TOPOLOGY"
        mod.data_types_loops = {'CUSTOM_NORMAL'}
        mod.object = clone
        bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
        bpy.ops.object.modifier_apply(modifier=mod.name)

    def delete_clone(self, clone):
        objs = bpy.data.objects
        objs.remove(objs[clone.name], do_unlink=True)

    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        total_fixed_vertices = 0
        
        for mesh_obj in selected_meshes:
            context.view_layer.objects.active = mesh_obj
            
            # Handle auto smooth
            if bpy.app.version < (4, 0, 0):
                if not mesh_obj.data.use_auto_smooth:
                    mesh_obj.data.use_auto_smooth = True
                    mesh_obj.data.auto_smooth_angle = 0.785  # 45 degrees
            
            # Set all polygons to smooth
            mesh_obj.data.polygons.foreach_set("use_smooth", [True] * len(mesh_obj.data.polygons))
            
            # Create clone for normal transfer
            clone = self.clone_mesh(mesh_obj)
            
            # Enter edit mode and prepare bmesh
            bpy.ops.object.mode_set(mode='EDIT')
            me = mesh_obj.data
            bm = bmesh.from_edit_mesh(me)
            
            # Store old seams
            old_seams = [e for e in bm.edges if e.seam]
            
            # Unmark old seams
            for e in old_seams:
                e.seam = False
            
            # Mark seams from UV islands
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.seams_from_islands()
            
            # Split edges at seams
            seams = [e for e in bm.edges if e.seam]
            bmesh.ops.split_edges(bm, edges=seams)
            
            # Restore old seams
            for e in old_seams:
                e.seam = True
            
            # Update mesh
            bmesh.update_edit_mesh(me)
            
            # Track fixed vertices
            old_vertex_count = len(bm.verts)
            
            # Solve repeated vertices
            self.solve_repeated_vertex(mesh_obj)
            
            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Transfer normals
            self.transfer_normals(clone, mesh_obj)
            
            # Final normal calculations
            if bpy.app.version < (4, 0, 0):
                mesh_obj.data.calc_normals_split()
            
            # Cleanup
            self.delete_clone(clone)
            
            # Reload bmesh to get updated vertex count
            bm = bmesh.new()
            bm.from_mesh(mesh_obj.data)
            new_vertex_count = len(bm.verts)
            
            # Calculate fixed vertices
            fixed_vertices = new_vertex_count - old_vertex_count
            total_fixed_vertices += fixed_vertices
            bm.free()
            
            # Mark as RE Engine optimized
            mesh_obj.kreed_re_engine_optimized = True
            mesh_obj.kreed_re4_og_optimized = False
        
        # Report with total fixed vertices
        if total_fixed_vertices > 0:
            self.report({'INFO'}, f"Fixed UVs on {len(selected_meshes)} meshes. Vertices fixed: {total_fixed_vertices}")
        else:
            self.report({'INFO'}, f"Fixed UVs on {len(selected_meshes)} meshes. No vertices needed fixing.")
        
        return {'FINISHED'}

class OBJECT_OT_force_weighted_normals(Operator):
    bl_idname = "object.force_weighted_normals"
    bl_label = "Weighted Normals"
    bl_description = "Apply weighted normals with default settings"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        # Enable Auto Smooth using the compatibility function
        set_auto_smooth(obj, True, 0.523599)  # 30 degrees
        
        # Apply weighted normals modifier
        modifier = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
        modifier.mode = 'FACE_AREA'  # Default setting
        modifier.weight = 50  # Default setting
        modifier.thresh = 0.01  # Default setting
        bpy.ops.object.modifier_apply(modifier="WeightedNormal")
        
        self.report({'INFO'}, "Applied weighted normals")
        return {'FINISHED'}



class OBJECT_OT_merge_and_weighted(Operator):
    bl_idname = "object.merge_and_weighted"
    bl_label = "Merge & Weighted Normal"
    bl_description = "Merge vertices by distance and apply weighted normals"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
    
        # Store original mode
        original_mode = context.mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
        # Prepare to count vertices
        original_vertex_count = len(obj.data.vertices)
    
        # Merge vertices by distance
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
    
        result = bpy.ops.mesh.remove_doubles(threshold=0.0001)
    
        bpy.ops.object.mode_set(mode='OBJECT')
        new_vertex_count = len(obj.data.vertices)
    
        merged_vertices = original_vertex_count - new_vertex_count
    
        # Enable Auto Smooth using the compatibility function
        set_auto_smooth(obj, True, 0.523599)  # 30 degrees
    
        # Apply weighted normals modifier
        modifier = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
        modifier.mode = 'FACE_AREA'  # Default setting
        modifier.weight = 50  # Default setting
        modifier.thresh = 0.01  # Default setting
        bpy.ops.object.modifier_apply(modifier="WeightedNormal")
    
        # Mark as RE4 OG optimized
        obj.kreed_re4_og_optimized = True
        obj.kreed_re_engine_optimized = False
    
        # Return to original mode if needed
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=original_mode)
    
        if merged_vertices > 0:
            self.report({'INFO'}, f"Merged {merged_vertices} vertices and applied weighted normals")
        else:
            self.report({'INFO'}, "No vertices merged. Applied weighted normals.")
    
        return {'FINISHED'}

class OBJECT_OT_cleanup_mesh(Operator):
    bl_idname = "object.cleanup_mesh"
    bl_label = "Cleanup Mesh"
    bl_description = "Perform complete mesh cleanup: delete loose, dissolve degenerate, merge by distance, and apply weighted normals"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
    
        # Store original mode
        original_mode = context.mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
        original_vertex_count = len(obj.data.vertices)
        original_polygon_count = len(obj.data.polygons)
    
        # Enter edit mode and select all
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
    
        bm = bmesh.from_edit_mesh(obj.data)
    
        # Delete loose geometry
        bpy.ops.mesh.delete_loose()
    
        # Dissolve degenerate
        bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    
        # Merge by distance
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
    
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        new_vertex_count = len(obj.data.vertices)
        new_polygon_count = len(obj.data.polygons)
    
        deleted_vertices = original_vertex_count - new_vertex_count
        deleted_polygons = original_polygon_count - new_polygon_count
    
        # Enable Auto Smooth using our compatibility function
        set_auto_smooth(obj, True, 0.523599)  # 30 degrees
    
        # Apply weighted normals modifier
        modifier = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
        modifier.mode = 'FACE_AREA'  # Default setting
        modifier.weight = 50  # Default setting
        modifier.thresh = 0.01  # Default setting
        bpy.ops.object.modifier_apply(modifier="WeightedNormal")
    
        # Return to original mode if it wasn't object mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=original_mode)
    
        report_messages = []
    
        if deleted_vertices > 0:
            report_messages.append(f"Deleted {deleted_vertices} vertices")
    
        if deleted_polygons > 0:
            report_messages.append(f"Deleted {deleted_polygons} polygons")
    
        if report_messages:
            self.report({'INFO'}, ". ".join(report_messages) + " and applied weighted normals")
        else:
            self.report({'INFO'}, "No geometry deleted. Applied weighted normals.")
    
        return {'FINISHED'}

class OBJECT_OT_toggle_face_orientation(Operator):
    bl_idname = "object.toggle_face_orientation"
    bl_label = "Toggle Face Orientation"
    bl_description = "Toggle face orientation display (blue=front, red=back)"
    
    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'VIEW_3D'
    
    def execute(self, context):
        # Toggle face orientation display
        context.space_data.overlay.show_face_orientation = not context.space_data.overlay.show_face_orientation
        
        # Report status
        status = "enabled" if context.space_data.overlay.show_face_orientation else "disabled"
        self.report({'INFO'}, f"Face orientation display {status}")
        
        return {'FINISHED'}

class VIEW3D_PT_kreed_utility_main(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "Kreed Utility"
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Mesh Utilities", icon='MESH_DATA')

class VIEW3D_PT_kreed_utility_info(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "Mesh Info"
    bl_parent_id = "VIEW3D_PT_kreed_utility_main"
    # Removed DEFAULT_CLOSED to have panel open by default
    
    @staticmethod
    def has_seams(obj):
        if obj.type != 'MESH':
            return False
        return any(edge.use_seam for edge in obj.data.edges)
    
    @staticmethod
    def needs_merge(obj):
        if obj.type != 'MESH':
            return False
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            result = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=0.0001)
            needs_merge = bool(result.get('targetmap', []))
            bm.free()
            return needs_merge
        except:
            return False

    @staticmethod
    def has_loose_geometry(obj):
        if obj.type != 'MESH':
            return False
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            loose_verts = [v for v in bm.verts if not v.link_edges]
            loose_edges = [e for e in bm.edges if not e.link_faces]
            
            has_loose = bool(loose_verts or loose_edges)
            bm.free()
            return has_loose
        except:
            return False
    
    @staticmethod
    def is_re_og_optimized(obj):
        """Check if mesh is optimized for RE4 OG"""
        return hasattr(obj, 'kreed_re4_og_optimized') and obj.kreed_re4_og_optimized
    
    @staticmethod
    def is_re_engine_optimized(obj):
        """Check if mesh is optimized for RE Engine"""
        return hasattr(obj, 'kreed_re_engine_optimized') and obj.kreed_re_engine_optimized
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
    
        if not obj or obj.type != 'MESH':
            layout.label(text="No mesh selected", icon='ERROR')
            return
            
        # Add Face Orientation toggle at the top
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Viewport Display:", icon='SHADING_RENDERED')
        col.operator("object.toggle_face_orientation", icon='FACESEL')
        
        # Mesh Statistics
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Statistics:", icon='INFO')
        row = col.row()
        row.label(text=f"Vertices: {len(obj.data.vertices):,}")
        row.label(text=f"Faces: {len(obj.data.polygons):,}")
    
        # UV Information
        box = layout.box()
        col = box.column(align=True)
        col.label(text="UV Status:", icon='UV')
    
        if not obj.data.uv_layers:
            col.label(text="No UV Maps", icon='ERROR')
        else:
            col.label(text=f"UV Maps: {len(obj.data.uv_layers)}", icon='CHECKMARK')
        
            # UV Seams status
            if self.has_seams(obj):
                col.label(text="UV Seams: Good", icon='CHECKMARK')
            else:
                col.label(text="UV Seams: Missing", icon='ERROR')
    
        # Mesh Status
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Mesh Status:", icon='MESH_DATA')
    
        if self.has_loose_geometry(obj):
            col.label(text="Has Loose Geometry", icon='ERROR')
            col.operator("object.cleanup_mesh", text="Run Full Cleanup", icon='BRUSH_DATA')
        elif self.is_re_og_optimized(obj):
            col.label(text="Optimized for RE4 OG", icon='CHECKMARK')
        elif self.is_re_engine_optimized(obj):
            col.label(text="Optimized for RE Engine", icon='CHECKMARK')
        else:
            # Determine optimization suggestions based on current state
            if not self.has_seams(obj):
                col.label(text="Requires UV Optimization", icon='ERROR')
                col.operator("object.solve_repeated_uvs", text="Solve Repeated UVs", icon='UV')
                col.operator("object.merge_and_weighted", text="Optimize for RE4 OG", icon='AUTOMERGE_OFF')
            elif self.needs_merge(obj):
                col.label(text="Requires Vertex Optimization", icon='ERROR')
                col.operator("object.merge_and_weighted", text="Optimize for RE4 OG", icon='AUTOMERGE_OFF')
                col.operator("object.solve_repeated_uvs", text="Solve Repeated UVs", icon='UV')
            else:
                # If both seams and merge are not immediately necessary, 
                # choose suggestion based on UV information
                if len(obj.data.uv_layers) == 0:
                    col.label(text="Requires UV Setup", icon='ERROR')
                    col.operator("object.solve_repeated_uvs", text="Solve Repeated UVs", icon='UV')
                    col.operator("object.merge_and_weighted", text="Optimize for RE4 OG", icon='AUTOMERGE_OFF')
                else:
                    col.label(text="Requires Optimization", icon='ERROR')
                    col.operator("object.merge_and_weighted", text="Optimize for RE4 OG", icon='AUTOMERGE_OFF')
                    col.operator("object.solve_repeated_uvs", text="Solve Repeated UVs", icon='UV')

class VIEW3D_PT_kreed_utility_vertex_groups(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "Vertex Groups"
    bl_parent_id = "VIEW3D_PT_kreed_utility_main"
    # Removed DEFAULT_CLOSED to have panel open by default
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.remove_empty_vertex_groups", icon='TRASH')
        col.operator("object.sort_vertex_groups", icon='SORTALPHA')
        col.operator("object.normalize_weights", icon='MOD_VERTEX_WEIGHT')
        col.separator()
        col.operator("object.mix_vertex_weights", icon='GROUP_VERTEX')

class VIEW3D_PT_kreed_utility_uv(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "UV Tools"
    bl_parent_id = "VIEW3D_PT_kreed_utility_main"
    # Removed DEFAULT_CLOSED to have panel open by default
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.solve_repeated_uvs", icon='UV')

class VIEW3D_PT_kreed_utility_normals(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "Normals"
    bl_parent_id = "VIEW3D_PT_kreed_utility_main"
    # Removed DEFAULT_CLOSED to have panel open by default
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.force_weighted_normals", icon='NORMALS_VERTEX')

class VIEW3D_PT_kreed_utility_cleanup(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kreed Utility'
    bl_label = "Mesh Cleanup"
    bl_parent_id = "VIEW3D_PT_kreed_utility_main"
    # Removed DEFAULT_CLOSED to have panel open by default
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.cleanup_mesh", icon='BRUSH_DATA')
        col.operator("object.merge_and_weighted", icon='AUTOMERGE_OFF')

classes = (
    OBJECT_OT_mix_vertex_weights,
    OBJECT_OT_remove_empty_vertex_groups,
    OBJECT_OT_sort_vertex_groups,
    OBJECT_OT_solve_repeated_uvs,
    OBJECT_OT_normalize_weights,
    OBJECT_OT_force_weighted_normals,
    OBJECT_OT_merge_and_weighted,
    OBJECT_OT_cleanup_mesh,
    OBJECT_OT_toggle_face_orientation,
    VIEW3D_PT_kreed_utility_main,
    VIEW3D_PT_kreed_utility_info,
    VIEW3D_PT_kreed_utility_vertex_groups,
    VIEW3D_PT_kreed_utility_uv,
    VIEW3D_PT_kreed_utility_normals,
    VIEW3D_PT_kreed_utility_cleanup,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Object.kreed_re_engine_optimized
    del bpy.types.Object.kreed_re4_og_optimized
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()