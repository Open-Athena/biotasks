"""Experimental recipe identity lookup; never executes a recipe or changes source."""
import json
from pathlib import Path


class AmbiguousRecipe(ValueError):
    pass


def resolve(local_ref, parse_tag, build_recipe, *, cache_dir=None):
    owner,name,short=parse_tag(local_ref)
    if not name or not short:
        return None,None
    key=(owner+'__'+name).casefold()
    roots=([Path(cache_dir)] if cache_dir is not None else [])+[
        Path('workspace/bootstrap'),Path('envs')]
    visited=set();matches=[]
    for root in roots:
        root=root.resolve()
        if root in visited or not root.is_dir():continue
        visited.add(root)
        for repo in sorted(root.iterdir()):
            if not repo.is_dir() or repo.is_symlink() or repo.name.casefold()!=key:continue
            for slot in sorted(repo.iterdir()):
                if not slot.is_dir() or slot.is_symlink() or not slot.name.startswith(short[:12]):continue
                path=slot/'bootstrap.json'
                if not path.is_file() or path.is_symlink():continue
                try:
                    data=json.loads(path.read_text())
                    # A short image tag cannot disambiguate option-hashed cache slots.
                    # Do not infer an identity from an arbitrary directory order.
                    if data.get('repo','').casefold()!=(owner+'/'+name).casefold():continue
                    if not data.get('ref','').startswith(short):continue
                    if data.get('image_tag') and data['image_tag']!=local_ref:continue
                    recipe=build_recipe(owner,name,data)
                    if recipe:matches.append((str(path),recipe))
                except (ValueError,OSError):continue
    if len(matches)>1:
        raise AmbiguousRecipe('Multiple cached recipes match '+local_ref)
    return (matches[0][1],'agent_replay') if matches else (None,None)
