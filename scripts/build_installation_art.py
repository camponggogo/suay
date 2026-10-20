"""Build editable isometric installation figures from SUAY's shared geometry."""
from html import escape
from pathlib import Path
import build_anatomy as art

OUT=Path(__file__).resolve().parents[1]/'landing/assets/install'
SPECS={
    'gateway':('Organization gateway','One management computer and the scoped-key gateway appliance.',{'app','gateway','auth','policy'}),
    'worker':('Petals compute agents','Server and mixed compute devices illustrate the experimental worker pool.',{'backend','pool'}),
    'client':('Terminal prompt client','A user workstation sends prompts after the compute agents are ready.',{'app'}),
    'rust':('Optional local Rust supervisor','One backend cabinet illustrates locally owned process supervision.',{'backend'}),
}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    art.model()
    for key,(title,description,groups) in SPECS.items():
        parts=[a for a in art.PARTS if a.group in groups]
        if key=='rust':
            # Fasteners securing the four backend sleds to the front rails.
            parts += [art.Part('sled mounting screw',xx,268,zz,3,2,3,'backend','screw')
                      for zz in (45,94,143,192) for xx in (671,675,767,771)]
        x=min(a.x for a in parts)-15; y=min(a.y for a in parts)-15
        xmax=max(a.x+a.w for a in parts)+15; ymax=max(a.y+a.d for a in parts)+15
        stage=[art.Part('setup plinth',x,y,4,xmax-x,ymax-y,12,material='metal')]
        for xx in (x+10,xmax-24):
            for yy in (y+10,ymax-24):
                stage.insert(0,art.Part('setup foot',xx,yy,-15,14,14,19,material='rubber'))
        c=art.Canvas()
        for a in stage: art.solid(c,a,3 if key in ('worker','rust') else 0)
        overlays={'CRT glass','screen prompt line','monitor power button','tower vent',
                  'tower drive bay','tower status lamp','gateway display glass','policy display bar',
                  'scope indicator','disk caddy','backend indicator','lid ventilation rib','lid fastener',
                  'key card socket','scoped key card','laptop glass','phone glass','phone app tile',
                  'phone speaker','laptop key','Pi processor','Pi USB block','Pi ethernet block',
                  'Pi GPIO pin','Pi activity LED','edge heatsink fin'}
        ordered=sorted(parts,key=lambda a:(a.x+a.y+.55*(a.w+a.d),a.z))
        for overlay in (False,True):
            for a in ordered:
                if (a.name in overlays)==overlay and a.material not in ('led','display'): art.solid(c,a,3 if key in ('worker','rust') else 0)
        for a in ordered:
            if a.material in ('led','display'): art.solid(c,a,3 if key in ('worker','rust') else 0)
        points=[art.p(a.x+dx,a.y+dy,a.z+dz) for a in parts+stage
                for dx in (0,a.w) for dy in (0,a.d) for dz in (0,a.h)]
        left=min(p[0] for p in points)-20;top=min(p[1] for p in points)-20
        width=max(p[0] for p in points)-left+20;height=max(p[1] for p in points)-top+20
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="460" viewBox="0 0 800 460" role="img" aria-labelledby="t d"><title id="t">{escape(title)}</title><desc id="d">{escape(description)}</desc><rect width="800" height="460" rx="20" fill="{art.BG}"/>'
        scale=min(752/width,412/height)
        tx=(800-width*scale)/2-left*scale;ty=(460-height*scale)/2-top*scale
        svg+=f'<g transform="translate({tx:.3f} {ty:.3f}) scale({scale:.5f})">'+''.join(c.svg[4:])+'</g></svg>'
        (OUT/(key+'.svg')).write_text(svg,encoding='utf-8')
        crop=c.image.crop((int(left),int(top),int(left+width+1),int(top+height+1)))
        crop.thumbnail((752,412))
        from PIL import Image
        preview=Image.new('RGB',(800,460),art.BG)
        preview.paste(crop,((800-crop.width)//2,(460-crop.height)//2))
        shots=OUT.parents[2]/'.preview/install'
        shots.mkdir(parents=True,exist_ok=True)
        preview.save(shots/(key+'.png'),optimize=True)
        print(key,len(parts),'parts')


if __name__=='__main__':main()
