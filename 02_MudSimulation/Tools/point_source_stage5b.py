"""Independent post-reader contract for PainterSourceData 1.3.

Inputs are already in Unit space. This does not implement original particle
readers, neighbor hashing, world transforms or invalid-reader behavior.
"""
from math import dist

def decode_source(index,tracked,data_channel,chaos,array_velocity=1.,particle_velocity=1.,kill_policy=0):
    if index<0 or index>=len(tracked)+len(data_channel)+len(chaos):
        raise IndexError('Outside valid-source contract; original DI failure values are not emulated')
    if index<len(tracked):
        kind=0;local=index;source=tracked[local]
        current=source['UnitVelocity'];previous=source['Previous.UnitVelocity']
        velocity=tuple(v*array_velocity for v in current) if dist(current,previous)<1 else (0.,0.,0.)
        pos=source['UnitPosition'];last=source['Previous.UnitPosition'];size=source['BrushScale']
        density=float(kill_policy not in (1,4,5))
    elif index<len(tracked)+len(data_channel):
        kind=1;local=index-len(tracked);source=data_channel[local]
        pos=source['position'];last=source['previous_position'];size=source['velocity_size'][3]
        velocity=tuple(v*particle_velocity for v in source['velocity_size'][:3])
        density=float(kill_policy not in (2,5))
    else:
        kind=2;local=index-len(tracked)-len(data_channel);source=chaos[local]
        pos=source['UnitPosition'];last=source['Previous.UnitPosition'];size=source['BrushScale']
        velocity=tuple(source['UnitVelocity']);density=float(kill_policy not in (3,4,5))
    return {'kind':kind,'local_index':local,'position':tuple(pos[:2]),'position_z':pos[2],
        'previous_position':tuple(last[:2]),'velocity':velocity,'size':size,'density_enable':density}

def source_index(iteration,neighbor_index=None):
    """UseNeighborGrid chooses the neighbor index instead of loop iteration."""
    return iteration if neighbor_index is None else neighbor_index

def verify():
    import json
    from pathlib import Path
    tracked=[{'UnitPosition':(.2,.3,.6),'Previous.UnitPosition':(.1,.25,.6),'UnitVelocity':(.2,-.1,0),
        'Previous.UnitVelocity':(.1,-.1,0),'BrushScale':.05}]
    channel=[{'position':(.7,.6,.55),'previous_position':(.65,.5,.55),'velocity_size':(-.3,.4,0,.08)}]
    chaos=[{'UnitPosition':(.9,.1,.7),'Previous.UnitPosition':(.8,.1,.7),'UnitVelocity':(-2,1,0),'BrushScale':.12}]
    rows=[]
    expected_density=[[1,1,1],[0,1,1],[1,0,1],[1,1,0],[0,1,0],[0,0,0]]
    expected_velocity=[(.4,-.2,0),(-.9,1.2,0),(-2,1,0)]
    for policy in range(6):
        values=[decode_source(i,tracked,channel,chaos,2,3,policy) for i in range(3)]
        assert [v['kind'] for v in values]==[0,1,2]
        assert [v['density_enable'] for v in values]==expected_density[policy]
        assert all(dist(v['velocity'],expected_velocity[i])<1e-12 for i,v in enumerate(values))
        assert [v['local_index'] for v in values]==[0,0,0]
        rows.append({'kill_policy':policy,'decoded':values})
    assert source_index(0,2)==2 and source_index(2)==2
    # Boundary moves with collection size; the data-channel item is index 0
    # when no tracked particles exist, and Chaos follows immediately after it.
    assert decode_source(0,[],channel,chaos)['kind']==1
    assert decode_source(1,[],channel,chaos)['kind']==2
    assert decode_source(0,[],[],chaos)['kind']==2
    tracked[0]['UnitVelocity']=(1.1,-.1,0)
    assert decode_source(0,tracked,channel,chaos)['velocity']==(0,0,0)
    result={'scope':__doc__,'cases':rows,'empty_collection_boundaries':True,'neighbor_index_selection':True,'velocity_jump_rejected':True,'pass':True}
    path=Path(__file__).resolve().parents[2]/'Verification/MudPainter/source_contract_verification.json'
    path.write_text(json.dumps(result,indent=2))
    return {'pass':True,'policy_source_combinations':18,'path':str(path)}

if __name__=='__main__':print(verify())
