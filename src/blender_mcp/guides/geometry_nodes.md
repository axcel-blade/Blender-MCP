# Geometry nodes

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Node and socket names change between versions: check them with
`lookup_api("GeometryNodeDistributePointsOnFaces")` (lists the sockets) before linking.

## When to use

Procedural, editable setups: scattering (rocks, grass, trees, crowds), arrays and patterns,
parametric objects (shelves, fences, stairs with a length input), procedural modelling,
instancing many copies cheaply, and simulation zones for custom effects.

## Inputs needed

- What the user should be able to change afterwards (expose those as group inputs:
  density, seed, count, size).
- The target surface or curve and the objects or collections to instance.
- Whether the result must become real geometry (export, sculpting) or can stay procedural.

## Workflow

1. Create a node group with Geometry in and out, and the exposed inputs.
2. Build the graph in small steps; after each step evaluate and check the result
   (`look`, or count points/instances from the depsgraph).
3. Use instances (Instance on Points) for repeated objects; realise them only when needed.
4. Randomise rotation and scale with Random Value; drive variation with the seed input.
5. Put the modifier on the target object; set inputs from the modifier, not the group,
   so the same group can be reused with other values.
6. Keep the group: reuse it on other objects, or mark it as an asset for the user.
7. Apply the modifier only when the user wants real geometry (`modifier_apply`).

## Tested values and code

```python
# [5.3] scatter cones over a surface: 199 instances at density 2 on 100 m2
ng = bpy.data.node_groups.new("Scatter", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
d = ng.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
d.default_value = 2.0; d.min_value = 0
ng.interface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt")
gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
dp = ng.nodes.new("GeometryNodeDistributePointsOnFaces")
ip = ng.nodes.new("GeometryNodeInstanceOnPoints")
cone = ng.nodes.new("GeometryNodeMeshCone")
join = ng.nodes.new("GeometryNodeJoinGeometry")
L = ng.links.new
L(gi.outputs["Geometry"], dp.inputs["Mesh"]); L(gi.outputs["Density"], dp.inputs["Density"])
L(gi.outputs["Seed"], dp.inputs["Seed"]); L(dp.outputs["Points"], ip.inputs["Points"])
L(cone.outputs["Mesh"], ip.inputs["Instance"]); L(ip.outputs["Instances"], join.inputs["Geometry"])
L(gi.outputs["Geometry"], join.inputs["Geometry"]); L(join.outputs["Geometry"], go.inputs["Geometry"])
mod = ob.modifiers.new("Scatter", "NODES"); mod.node_group = ng
```

Set a modifier input by name. The API changed in 5.x [5.3]: `mod["Socket_2"] = v` raises
"doesn't support IDProperties"; values now live on `mod.properties.inputs`:

```python
def set_input(mod, name, value):
    item = next(i for i in mod.node_group.interface.items_tree
                if getattr(i, "in_out", None) == "INPUT" and i.name == name)
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):     # 5.x [5.3]
        getattr(props.inputs, item.identifier).value = value
    else:                                                   # 4.x [untested]
        mod[item.identifier] = value
    mod.id_data.update_tag()
```

  Tested [5.3]: Density 8 gave 800 instances (from 199 at 2).
- Count instances: `sum(1 for i in depsgraph.object_instances if i.is_instance and
  i.parent and i.parent.original == ob)` after `depsgraph.update()`.
- `node_group.interface` exists from 4.0; before that use `ng.inputs.new(...)` /
  `ng.outputs.new(...)` [untested].
- Zones and nodes available in 5.3: simulation (`GeometryNodeSimulationInput`, 4.0+), repeat
  (`GeometryNodeRepeatInput`, 4.0+), for-each element
  (`GeometryNodeForeachGeometryElementInput`, 4.3+), and `GeometryNodeBake`.
- Distribute Points on Faces inputs [5.3]: Mesh, Selection, Distance Min, Density Max,
  Density, Density Factor, Seed. Density is per m2: 0.5-2 for trees, 20-200 for grass tufts.
- Instancing a collection [5.3]: Collection Info node with its "Separate Children" and
  "Reset Children" input sockets set to True (`node.inputs["Separate Children"].default_value`),
  into Instance on Points' "Instance" socket with its "Pick Instance" socket True.

## Common mistakes

- Linking sockets by index: indices shift between versions. Link by name and check names
  with lookup_api.
- Setting the group's `default_value` and expecting existing modifiers to change: set the
  modifier input instead.
- Realising millions of instances: memory explodes. Keep instances until export.
- Huge densities on large surfaces (density x area = points): check area first.
- Scale not applied on the target: densities and sizes come out wrong.
- Editing a node group shared by other objects: duplicate it first (`ng.copy()`).

## Verification checklist

- [ ] Point and instance counts are in the expected range (density x area).
- [ ] Changing seed and density on the modifier updates the result.
- [ ] `look(mode="material")` from the camera shows natural variation, no regular grid.
- [ ] Viewport stays responsive; heavy parts limited with a viewport density factor.
- [ ] Group and inputs named clearly for the user to edit later.

## Manual work and external tools

- Complex node trees are easier to tweak in the node editor by hand: build the base and
  leave tuning to the user.
- Ready-made node assets (e.g. Blender's Essentials, community node packs) must be added
  by the user. Asset libraries are set in Preferences and add-ons must be enabled by the
  user; safe execution mode refuses changing preferences and enabling add-ons. Explain
  that and never bypass it.
