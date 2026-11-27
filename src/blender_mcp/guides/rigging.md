# Rigging

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Check uncertain names with `lookup_api`. Animating the finished rig is in
`animation_3d`; engine export in `game_assets`.

## When to use

Making a mesh posable: characters, creatures, mechanical arms, doors and hinges, vehicles,
props with moving parts. Simple rigid parts can often be parented to an Empty instead of
using an armature.

## Inputs needed

- The mesh, in rest pose (T- or A-pose for characters), scale applied, facing -Y.
- What must move and how: deform (skin bends) or rigid (parts rotate as a whole).
- Destination: animation in Blender (controls and IK welcome) or a game engine (a clean
  deform-only hierarchy, no constraints that won't export).

## Workflow

1. Check the mesh: applied scale and rotation, clean normals, edge loops at joints
   (elbows, knees need 3 loops), one connected or properly parented set of parts.
2. Armature in Edit Mode: a `root` bone at the origin, then the hierarchy outwards
   (hips -> spine -> chest -> neck -> head; shoulder -> upper arm -> forearm -> hand).
   Name sides with `.L` / `.R` so mirroring and symmetry tools work.
3. Bend direction: give elbows and knees a slight bend in rest pose so IK knows which way
   to fold. Set bone roll consistently (`bpy.ops.armature.calculate_roll`).
4. Organise: bone collections (`Deform`, `Controls`, `Mechanics`); turn off `use_deform`
   on non-deforming bones.
5. Controls: IK on limbs (chain_count 2) with a pole target, Copy Rotation / Damped Track
   for eyes and aim, custom shapes for animator controls.
6. Skin: `parent_set(type="ARMATURE_AUTO")` for automatic weights; rigid parts get
   weights of 1.0 on one bone (or plain parenting to a bone).
7. Test poses: rotate each control through its range, look, fix weights, then return to
   rest pose.

## Tested values and code

```python
# [5.3] build bones in Edit Mode, constraints in Pose Mode
arm = bpy.data.armatures.new("Rig"); rig = bpy.data.objects.new("Rig", arm)
collection.objects.link(rig); view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
root = arm.edit_bones.new("root"); root.head = (0, 0, 0); root.tail = (0, 0, 0.5)
up = arm.edit_bones.new("upper"); up.head = (0, 0, 0.5); up.tail = (0, 0, 1.0)
up.parent = root; up.use_connect = True
bpy.ops.object.mode_set(mode="POSE")
ik = rig.pose.bones["lower"].constraints.new("IK"); ik.chain_count = 2
bpy.ops.object.mode_set(mode="OBJECT")
# skin: select mesh, then the rig, rig active
mesh_ob.select_set(True); rig.select_set(True); view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")   # adds vertex groups + Armature modifier
```

- Bone collections [5.3, 4.0+]: `bc = arm.collections.new("Deform"); bc.assign(arm.bones["upper"])`.
  Before 4.0 bones used `arm.layers` / `bone.layers` (32 layers) [untested].
- Pose bones default to `rotation_mode = "QUATERNION"` [5.3]; switch controls to
  `"XYZ"` (or a suitable Euler order) if animators prefer Euler curves.
- Typical bone lengths for a 1.8 m human: spine segments 0.12-0.15 m, upper arm 0.28 m,
  forearm 0.26 m, thigh 0.45 m, shin 0.43 m.
- Weight values: 1.0 full influence, blends of 0.5 across 2-3 edge loops at joints. Keep
  each vertex to 4 or fewer bones for game engines, and normalise.
- Edit bones exist only in Edit Mode, pose bones only make sense in Pose Mode; read
  `arm.bones` (rest data) in any mode.

## Common mistakes

- Unapplied object scale on mesh or rig: bones and weights look right, then everything
  explodes when posed or exported.
- Straight limbs: IK bends the wrong way. Add a small bend and a pole target.
- Automatic weights fail ("Bone Heat Weighting failed") on non-manifold or overlapping
  meshes: merge by distance, fix the mesh, or weight by hand / with Data Transfer.
- Control bones left deforming: the mesh moves twice. Set `use_deform = False`.
- Editing `edit_bones` outside Edit Mode: the list is empty or changes are lost.
- Constraints (IK, Copy Rotation) don't export to engines: bake the action to deform bones
  first (`bpy.ops.nla.bake` with `visual_keying=True`).

## Verification checklist

- [ ] Rest pose unchanged after testing (pose cleared: `bpy.ops.pose.transforms_clear()`).
- [ ] Every deforming vertex belongs to at least one group; weights normalised.
- [ ] Extreme poses (arms up, knees bent 90 degrees, head turned) look acceptable from
      `look(mode="angles")`; no candy-wrapper twists or collapsing joints.
- [ ] Bones named with `.L`/`.R`, organised in bone collections, controls non-deforming.
- [ ] For engines: single root, no leaf bones needed, export and re-import keeps poses.

## Manual work and external tools

- Weight painting polish is hand work in Weight Paint mode.
- Full character rigs are faster with Rigify (bundled add-on) or Auto-Rig Pro; the user
  must enable them, because safe execution mode refuses enabling add-ons and registering
  classes. Explain that and never bypass it. Rig UI scripts that register panels or
  handlers are refused for the same reason.
- Facial rigs and corrective shape keys need artistic judgement; propose a plan and let the
  user drive.
- Mixamo can auto-rig humanoids externally; import the FBX and check scale.
