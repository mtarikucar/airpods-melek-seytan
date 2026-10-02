"""Meshy figürünü kapalı katıya çevirir: 30 mm boya ölçekler, 0,03 mm voksel ile yeniden örnekler,
küçük kopuk parçaları atar. Yön değiştirmez (Meshy STL: +Z yukarı).

blender -b --factory-startup --python scripts/solidify_figure.py -- raw/melek/stl.stl work/melek_solid.stl
"""
import bpy, sys
src, out = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=src)
o = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = o
zs = [v.co.z for v in o.data.vertices]
s = 30.0 / (max(zs) - min(zs))
o.scale = (s, s, s)
bpy.ops.object.transform_apply(scale=True)
m = o.modifiers.new('vox', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = 0.03; m.adaptivity = 0.0
bpy.ops.object.modifier_apply(modifier='vox')
# küçük kopuk parçaları sil
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
parts = sorted(bpy.context.selected_objects, key=lambda p: -len(p.data.vertices))
print('parts', [len(p.data.vertices) for p in parts[:8]])
for p in parts[1:]:
    if len(p.data.vertices) < 0.002 * len(parts[0].data.vertices):
        bpy.data.objects.remove(p)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = parts[0]
if len(bpy.context.selected_objects) > 1:
    bpy.ops.object.join()
bpy.ops.wm.stl_export(filepath=out, export_selected_objects=True)
print('wrote', out, len(bpy.context.active_object.data.vertices))
