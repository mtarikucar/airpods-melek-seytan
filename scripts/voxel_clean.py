"""STL'yi Blender voksel yeniden örnekleme ile kapalı, temiz katıya çevirir (yerinde).
blender -b --factory-startup --python scripts/voxel_clean.py -- dosya.stl 0.05"""
import bpy, sys
f, vs = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=f)
o = bpy.context.selected_objects[0]; bpy.context.view_layer.objects.active = o
m = o.modifiers.new('vox', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = float(vs); m.adaptivity = 0.0
bpy.ops.object.modifier_apply(modifier='vox')
bpy.ops.wm.stl_export(filepath=f, export_selected_objects=True)
print('cleaned', f, len(o.data.vertices))
