// Constructor del paquete gráfico. No importa ni modifica el proyecto de ajedrez.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const sharp = require('sharp');
const ROOT = path.resolve(__dirname, '..');
const SIZES = [60, 120, 240];
const C = { marfil:'#FAF7EE', grafito:'#252A30', rojo:'#B8323C', azul:'#2563A6', verde:'#28784A', ambar:'#D49A28', secundario:'#58616A' };
const palettes = {
 club:{clara:'#E8E6D5',oscura:'#789078',fondo:'#F3F1E8'},
 taller:{clara:'#E4CEAA',oscura:'#986F4F',fondo:'#F1E9DB'},
 pizarra:{clara:'#D6DFE3',oscura:'#708895',fondo:'#E9EEF0'}
};
const finishes = ['liso_mate','microfibra','veta_fina','mineral_suave'];
const textureTheme = {microfibra:'club',veta_fina:'taller',mineral_suave:'pizarra'};
const shapes = {
 rey:{
  outer:'<path d="M47 10H53V18H60V24H53V31C64 25 77 30 76 41C75 49 67 56 62 62L64 73L70 79L72 89H28L30 79L36 73L38 62C33 56 25 49 24 41C23 30 36 25 47 31V24H40V18H47Z"/>',
  detail:'<path d="M38 62H62M36 73H64M31 80H69M50 33V49"/>'
 },
 dama:{
  outer:'<path d="M39 54H61L60 63L65 75L71 81L73 89H27L29 81L35 75L40 63Z"/><path d="M27 23L37 55H63L73 23L61 39V19L53 37L50 16L47 37L39 19V39Z"/><circle cx="27" cy="23" r="2.8"/><circle cx="39" cy="19" r="2.8"/><circle cx="50" cy="16" r="2.8"/><circle cx="61" cy="19" r="2.8"/><circle cx="73" cy="23" r="2.8"/>',
  detail:'<path d="M39 62H61M35 75H65M30 82H70"/>'
 },
 alfil:{
  outer:'<path d="M50 16C44 22 31 35 31 44C31 52 38 57 44 58L42 65L38 73L30 81L27 89H73L70 81L62 73L58 65L56 58C65 56 70 51 70 44C70 39 67 34 63 29L50 42L46 38L60 24C56 20 52 17 50 16Z"/>',
  detail:'<path d="M44 58H56M42 65H58M38 73H62M31 82H69"/>'
 },
 caballo:{
  outer:'<path d="M28 81C31 74 37 68 39 58L33 62L23 57L25 47L35 34L40 20L47 26L56 20C68 25 76 39 75 54C74 65 67 72 67 79L74 84V90H26V84Z"/>',
  detail:'<path d="M51 34C62 43 59 55 52 67M26 53L33 55M31 82H69"/><circle cx="42" cy="40" r="2" stroke="none" fill="currentColor"/>'
 },
 torre:{
  outer:'<path d="M27 25H38V34H45V25H55V34H62V25H73V43H67L64 74L72 81V89H28V81L36 74L33 43H27Z"/>',
  detail:'<path d="M33 43H67M36 74H64M29 82H71"/>'
 },
 peon:{
  outer:'<path d="M50 29C36 29 35 45 44 49V56C39 61 36 67 35 74L29 81L27 89H73L71 81L65 74C64 67 61 61 56 56V49C65 45 64 29 50 29Z"/>',
  detail:'<path d="M44 56H56M35 74H65M30 82H70"/>'
 }
};
const resources = {};
const saved = new Map();
const textureData = {};
const textureBounds = {};
function lum(rgb) {
 const c=rgb.map(v=>{const x=v/255;return x<=0.04045?x/12.92:Math.pow((x+0.055)/1.055,2.4);});
 return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
}
function textureOpacity(base,finish,side) {
 const rgb=base.slice(1).match(/../g).map(x=>parseInt(x,16));
 const bound=textureBounds[textureTheme[finish]+'_'+side],ref=lum(rgb);
 for(let a=0.80;a>=0.02;a-=0.02) {
  const delta=Math.max(...[bound.min,bound.max].map(edge=>Math.abs(lum(rgb.map((v,i)=>Math.round(v*(1-a)+edge[i]*a)))-ref)));
  if(delta<=0.012) return Number(a.toFixed(2));
 }
 return 0.02;
}
const manifest = {
 version:'1.0.0',fecha:'2026-09-28',estado:'recursos_preparados_sin_integracion_GUI',
 idioma:'es',tamanos_casilla_px:SIZES,coordenadas_svg:'viewBox: 0 0 100 100 equivale a una casilla',
 colores:C,paletas:palettes,acabados:finishes,temas:{},
 tipografia:{
  interfaz:{familia:'Segoe UI',alternativas:['Arial','TkDefaultFont'],tamano_px:16,peso:'normal',color:C.grafito},
  titulo:{familia:'Georgia',alternativas:['Times New Roman','TkDefaultFont'],tamano_px:28,peso:'normal',color:C.grafito},
  subtitulo:{familia:'Segoe UI',alternativas:['Arial','TkDefaultFont'],tamano_px:16,peso:'normal',color:C.secundario},
  coordenada:{familia:'Segoe UI',alternativas:['Arial','TkDefaultFont'],tamano_relativo_casilla:0.22,peso:'normal',color:C.grafito,ubicacion:'banda_exterior'},
  secuencia:{familia:'Segoe UI',alternativas:['Arial','TkDefaultFont'],tamano_relativo_casilla:0.20,peso:'bold',color:C.grafito,fondo:C.marfil},
  nota:'Perfiles de fuente, no ficheros TTF redistribuidos. Los PNG de glifos son auxiliares; para texto dinámico usar la fuente.'
 },
 textos:{anotar:'Anotar',ocultar_marcas:'Ocultar marcas',limpiar:'Limpiar',hipotesis:'Hipótesis',idea:'Idea',respuesta:'Respuesta',atencion:'Atención',apoyo:'Apoyo',jaque:'Jaque',promocion:'Elige la pieza de promoción',turno_blancas:'Juegan blancas',turno_negras:'Juegan negras'},
 geometria:{
  flecha:{ancho_trazo_s:0.07,ancho_halo_s:0.12,cabeza_largo_s:0.24,cabeza_ancho_s:0.24,patron_discontinuo_s:[0.12,0.08],extremos:'centros_de_casillas',nota:'PNG horizontal es muestra utilizable a su tamaño nativo; no estirarlo para otros recorridos. Dibujar la geometría entre origen y destino.'},
  caballo:{trayecto:'dos_casillas_y_una_perpendicular',nota:'Convención de desplazamiento, no regla de colisiones.'},
  anillo:{radio_s:0.40,ancho_s:0.05},
  seleccion:{margen_s:0.045,ancho_exterior_s:0.065,ancho_interior_s:0.025},
  punto_legal:{radio_s:0.09},
  distintivo:{ancla:'esquina_superior_derecha',diametro_s:0.24}
 },
 capas:['casillas','tintes','flechas','piezas','contornos_y_distintivos','texto_y_foco'],
 contratos:{
  manual:'Las anotaciones no implican legalidad, amenaza calculada ni jaque.',
  hipotesis:'Las proyecciones no cambian tablero aceptado, turno, historial ni promoción pendiente.',
  promocion:'Usar las mismas imágenes de dama/torre/alfil/caballo. El menú es una composición, no otra pieza.',
  propiedad_imagen:'Conservar una referencia al objeto de imagen mientras la GUI lo muestre.',
  flechas:'Para recorridos arbitrarios usar geometria y estilos; los recursos PNG incluidos tienen longitud y orientación documentadas.'
 },
 recursos:resources
};
function put(rel,data) {
 const target=path.resolve(ROOT,rel);
 if(!target.startsWith(ROOT+path.sep)) throw new Error('Destino fuera del paquete');
 fs.mkdirSync(path.dirname(target),{recursive:true});
 fs.writeFileSync(target,data);
}
function svg(body,w=100,h=100,defs='',scale=1) {
 return '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="'+(w*scale)+'" height="'+(h*scale)+'" viewBox="0 0 '+w+' '+h+'"><defs>'+defs+'</defs>'+body+'</svg>';
}
function paint(body,fill,stroke,width=3,extra='') {
 return '<g fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+width+'" stroke-linecap="round" stroke-linejoin="round" '+extra+'>'+body+'</g>';
}
function texture(finish,side) {return textureData[(textureTheme[finish]||'')+'_'+side];}
function textureImage(data,opacity) {
 return '<image width="100" height="100" preserveAspectRatio="none" opacity="'+opacity+'" xlink:href="data:image/png;base64,'+data+'"/>';
}
async function emit(id,category,body,{w=100,h=100,defs='',transparent=true,description='',extra={}}={}) {
 const prefix=id.replaceAll('.','/');
 const source='svg/'+prefix+'.svg';
 put(source,svg(body,w,h,defs));
 const entries={};
 for(const s of SIZES) {
  const rel='png/'+s+'/'+prefix+'.png';
  const buffer=await sharp(Buffer.from(svg(body,w,h,defs,s/100))).png().toBuffer();
  put(rel,buffer);
  entries[s]={archivo:rel,ancho:Math.round(w*s/100),alto:Math.round(h*s/100)};
 }
 resources[id]={id,tipo:category,descripcion:description,svg:source,png:entries,transparente:transparent,ancla:'centro',...extra};
 saved.set(id,{body,w,h,defs});
}
function pieceBody(role,side,finish,ghost=false,reinforced=false) {
 const sh=shapes[role], fill=side==='blanca'?C.marfil:C.grafito;
 const stroke=side==='blanca'?C.grafito:C.marfil;
 const uid=role+'_'+side+'_'+finish+(ghost?'_g':'');
 const defs='<clipPath id="'+uid+'">'+sh.outer+'</clipPath>';
 let body='';
 if(ghost) {
  body=paint(sh.outer,fill,'none',0,'fill-opacity=".14"');
  body+=paint(sh.outer,'none',side==='blanca'?C.marfil:C.grafito,5,'stroke-dasharray="6 4"');
  body+=paint(sh.outer,'none',stroke,2.8,'stroke-dasharray="6 4"');
  body+=paint(sh.detail,'none',stroke,2,'color="'+stroke+'" opacity=".65"');
 } else {
  body=paint(sh.outer,fill,'none',0);
  if(finish!=='liso_mate') body+='<g clip-path="url(#'+uid+')">'+textureImage(texture(finish,side==='blanca'?'clara':'oscura'),0.12)+'</g>';
  if(side==='negra') body+=paint(sh.outer,'none',C.grafito,reinforced?6:4.4);
  body+=paint(sh.outer,'none',stroke,reinforced?4.5:3.0);
  body+=paint(sh.detail,'none',stroke,reinforced?3.2:2.2,'color="'+stroke+'"');
 }
 return {body,defs};
}
function ring(color,r=40,width=5) {
 return '<circle cx="50" cy="50" r="'+r+'" fill="none" stroke="'+C.marfil+'" stroke-width="'+(width+3)+'"/><circle cx="50" cy="50" r="'+r+'" fill="none" stroke="'+color+'" stroke-width="'+width+'"/>';
}
function frame(color,fillOpacity=0) {
 return '<rect x="0" y="0" width="100" height="100" fill="'+color+'" opacity="'+fillOpacity+'"/><rect x="5" y="5" width="90" height="90" rx="2" fill="none" stroke="'+C.marfil+'" stroke-width="8"/><rect x="5" y="5" width="90" height="90" rx="2" fill="none" stroke="'+color+'" stroke-width="4"/>';
}
function arrow(color,dashed=false,knight=false) {
 const line=knight?'M50 250V50H126':'M50 50H226';
 const head=knight?'M150 50L126 38V62Z':'M250 50L226 38V62Z';
 const under=color===C.ambar?C.grafito:C.marfil;
 const dash=dashed?' stroke-dasharray="12 8"':'';
 const start='<path d="'+line+'" fill="none" stroke-linecap="butt" stroke-linejoin="round"';
 return start+' stroke="'+under+'" stroke-width="12"'+dash+'/>'+start+' stroke="'+color+'" stroke-width="7"'+dash+'/><path d="'+head+'" fill="'+color+'" stroke="'+under+'" stroke-width="2.5" stroke-linejoin="round"/>';
}
async function build() {
 if(fs.existsSync(path.join(ROOT,'catalogo.json'))&&!process.argv.includes('--rebuild')) throw new Error('Paquete existente; --rebuild sólo regenera sus recursos propios.');
 for(const name of ['club','taller','pizarra']) for(const side of ['clara','oscura']) {
  const rel='originales/texturas/'+name+'_'+side+'.png';
  const full=path.join(ROOT,rel);
  const meta=await sharp(full).metadata();
  // Reducción técnica para incrustar en los maestros SVG; no se altera el original.
  const png=await sharp(full).resize(256,256).png().toBuffer();
  textureData[name+'_'+side]=png.toString('base64');
  const raw=await sharp(png).removeAlpha().raw().toBuffer();
  const bound={min:[255,255,255],max:[0,0,0]};
  for(let i=0;i<raw.length;i+=3) for(let c=0;c<3;c++){bound.min[c]=Math.min(bound.min[c],raw[i+c]);bound.max[c]=Math.max(bound.max[c],raw[i+c]);}
  textureBounds[name+'_'+side]=bound;
  resources['textura.'+name+'.'+side]={id:'textura.'+name+'.'+side,tipo:'textura_original',archivo:rel,ancho:meta.width,alto:meta.height,transparente:false,nota:'Original ImageGen. Usar material compuesto del catálogo para contraste moderado; no se garantiza periodicidad matemática.'};
 }
 for(const [theme,pal] of Object.entries(palettes)) {
  await emit('fondo.'+theme,'fondo','<rect width="100" height="100" fill="'+pal.fondo+'"/>',{transparent:false,extra:{color:pal.fondo,repetible:true}});
  for(const finish of finishes) {
   const name=theme+'.'+finish;
   manifest.temas[name]={paleta:theme,acabado:finish,casilla_clara:'casilla.'+name+'.clara',casilla_oscura:'casilla.'+name+'.oscura',familia_piezas:'pieza.'+finish,proyecciones:'proyeccion.'+finish,fondo:'fondo.'+theme,tipografia:'compartida',ayudas:'compartidas'};
   for(const side of ['clara','oscura']) {
    let body='<rect width="100" height="100" fill="'+pal[side]+'"/>';
    const opacity=finish==='liso_mate'?0:textureOpacity(pal[side],finish,side);
    if(finish!=='liso_mate') body+=textureImage(texture(finish,side),opacity);
    await emit('casilla.'+name+'.'+side,'casilla',body,{transparent:false,extra:{color_base:pal[side],acabado:finish,opacidad_textura:opacity}});
   }
  }
 }
 for(const finish of finishes) for(const side of ['blanca','negra']) for(const role of Object.keys(shapes)) {
  for(const ghost of [false,true]) {
   const item=pieceBody(role,side,finish,ghost);
   await emit((ghost?'proyeccion.':'pieza.')+finish+'.'+side+'.'+role,ghost?'proyeccion':'pieza',item.body,{defs:item.defs,extra:{bando:side,rol:role,acabado:finish,requiere_rotulo:ghost?'Hipótesis':null}});
  }
 }
 for(const side of ['blanca','negra']) for(const role of Object.keys(shapes)) {
  const item=pieceBody(role,side,'liso_mate',false,true);
  await emit('pieza.reforzada.'+side+'.'+role,'pieza',item.body,{defs:item.defs,extra:{bando:side,rol:role,acabado:'liso_reforzado'}});
 }
 await emit('marca.seleccion','marca',frame(C.grafito));
 await emit('marca.foco','marca',paint('<path d="M6 25V6H25M75 6H94V25M94 75V94H75M25 94H6V75"/>','none',C.marfil,8)+paint('<path d="M6 25V6H25M75 6H94V25M94 75V94H75M25 94H6V75"/>','none',C.grafito,4)+'<path d="M45 96L50 89L55 96Z" fill="'+C.grafito+'"/>');
 await emit('marca.destino_legal','marca','<circle cx="50" cy="50" r="10.5" fill="'+C.marfil+'"/><circle cx="50" cy="50" r="9" fill="'+C.grafito+'"/>');
 await emit('marca.captura_legal','marca',ring(C.grafito,42,4));
 await emit('marca.atencion','marca',ring(C.rojo));
 await emit('marca.jaque','marca',frame(C.rojo,0.10)+'<circle cx="83" cy="17" r="11" fill="'+C.rojo+'" stroke="'+C.marfil+'" stroke-width="2"/><path d="M83 10V18M83 22V23" stroke="'+C.marfil+'" stroke-width="3" stroke-linecap="round"/>');
 await emit('marca.promocion_pendiente','marca',frame(C.azul,0.06)+'<path d="M76 14H90M83 7V21" stroke="'+C.azul+'" stroke-width="3"/>');
 for(const which of ['origen','destino']) {
  let body='<rect width="100" height="100" fill="'+C.ambar+'" fill-opacity=".18"/>';
  const corners='<path d="M5 20V5H20M80 5H95V20M95 80V95H80M20 95H5V80"/>';
  body+=paint(corners,'none',C.grafito,5)+paint(corners,'none',C.ambar,2);
  body+='<circle cx="13" cy="13" r="5" fill="'+(which==='origen'?C.marfil:C.grafito)+'" stroke="'+C.grafito+'" stroke-width="2"/>';
  await emit('marca.ultima_jugada_'+which,'marca',body);
 }
 for(const [key,col] of Object.entries({rojo:C.rojo,azul:C.azul,verde:C.verde,ambar:C.ambar})) {
  await emit('marca.circulo_'+key,'marca',ring(col));
  await emit('marca.fondo_'+key,'marca','<rect width="100" height="100" fill="'+col+'" fill-opacity=".16"/>',{extra:{es_relleno_auxiliar:true,no_usar_como_unica_senal:true}});
  for(const form of ['continua','discontinua','caballo']) await emit('flecha.'+key+'.'+form,'flecha',arrow(col,form==='discontinua',form==='caballo'),{w:form==='caballo'?200:300,h:form==='caballo'?300:100,extra:{color:col,forma:form,origen_svg:form==='caballo'?[50,250]:[50,50],destino_svg:form==='caballo'?[150,50]:[250,50],orientacion:form==='caballo'?'arriba_y_derecha':'derecha',uso:'Muestra PNG fija y maestro SVG; recorridos variables requieren geometría.'}});
 }
 // Distintivos sin depender de una fuente para los trazos esenciales.
 await emit('distintivo.atencion','distintivo','<path d="M50 12L92 86H8Z" fill="'+C.rojo+'" stroke="'+C.marfil+'" stroke-width="4"/><path d="M50 34V58M50 70V73" stroke="'+C.marfil+'" stroke-width="7" stroke-linecap="round"/>');
 await emit('distintivo.apoyo','distintivo','<circle cx="50" cy="50" r="39" fill="'+C.verde+'" stroke="'+C.marfil+'" stroke-width="4"/><path d="M38 29V71H48C75 71 75 29 48 29Z" fill="none" stroke="'+C.marfil+'" stroke-width="6"/>');
 // Iconos de controles presentes en las maquetas, con significado en el catálogo.
 const icons={
  anotar:'<path d="M25 65L65 25L77 37L37 77L22 80Z M58 32L70 44"/>',
  ocultar:'<path d="M9 50Q50 8 91 50Q50 92 9 50Z M15 15L85 85"/><circle cx="50" cy="50" r="15"/>',
  limpiar:'<path d="M22 27H78M39 27V17H61V27M29 27L34 84H66L71 27M43 41V70M57 41V70"/>'
 };
 for(const [id,body] of Object.entries(icons)) for(const tone of ['grafito','marfil']) await emit('icono.'+id+'.'+tone,'icono','<g transform="scale(.4)">'+paint(body,'none',C[tone],5)+'</g>',{w:40,h:40,extra:{color:C[tone],accion:id}});
 // Letras/números son glifos auxiliares; fuente y estilo siguen siendo recursos independientes.
 for(const ch of 'abcdefgh12345678') {
  for(const tone of ['grafito','marfil']) {
   const body='<text x="12.5" y="23" text-anchor="middle" font-family="Segoe UI" font-size="22" fill="'+C[tone]+'">'+ch+'</text>';
   await emit('glifo.'+tone+'.'+ch,'glifo',body,{w:25,h:30,extra:{texto:ch,perfil_tipografico:'coordenada',nota:'Glifo auxiliar, altura de fuente 22% de la casilla; para texto dinámico usar el perfil de fuente.'}});
  }
 }
 for(let n=1;n<=10;n++) await emit('secuencia.'+n,'secuencia','<circle cx="15" cy="15" r="13" fill="'+C.marfil+'" stroke="'+C.grafito+'" stroke-width="1.5"/><text x="15" y="21" text-anchor="middle" font-family="Segoe UI" font-size="'+(n===10?16:20)+'" font-weight="bold" fill="'+C.grafito+'">'+n+'</text>',{w:30,h:30,extra:{valor:n,nota:'Modelo ampliable; números mayores se dibujan con el perfil secuencia.'}});
 // Muestras de tipografía identificadas explícitamente, no textos de interfaz aplanados.
 for(const [id,txt,family,size,color] of [
  ['titulo','Ajedrez · Club','Georgia',32,C.grafito],
  ['interfaz','Anotar   Ocultar marcas   Limpiar','Segoe UI',18,C.grafito],
  ['coordenadas','a b c d e f g h    1 2 3 4 5 6 7 8','Segoe UI',18,C.grafito],
  ['estados','Hipótesis · Jaque · Promoción','Segoe UI',18,C.secundario]
 ]) await emit('tipografia.muestra_'+id,'muestra_tipografica','<text x="12" y="47" font-family="'+family+'" font-size="'+size+'" fill="'+color+'">'+txt+'</text>',{w:420,h:70,extra:{texto:txt,familia:family,tamano_svg:size}});
 // Fondos y contornos del control, separados del icono y del texto.
 await emit('control.boton_principal','control','<rect x="2" y="2" width="236" height="56" rx="7" fill="'+C.grafito+'"/>',{w:240,h:60,extra:{texto_perfil:'interfaz',texto_color:C.marfil}});
 await emit('control.boton_secundario','control','<rect x="2" y="2" width="236" height="56" rx="7" fill="none" stroke="'+C.secundario+'" stroke-width="2"/>',{w:240,h:60,extra:{texto_perfil:'interfaz',texto_color:C.grafito}});
 await emit('control.divisor','control','<path d="M0 5H300" stroke="'+C.secundario+'" stroke-width="1.5" opacity=".35"/>',{w:300,h:10});
 put('catalogo.json',JSON.stringify(manifest,null,2)+'\n');
 // Atlas de comprobación: los recursos reales se componen sobre las casillas reales.
 const tiles=[];
 const W=1440,H=1420;
 tiles.push({input:Buffer.from(svg('<rect width="'+W+'" height="'+H+'" fill="#F3F1E8"/><text x="40" y="48" font-family="Segoe UI" font-size="28" fill="'+C.grafito+'">Ajedrez · recursos gráficos v1</text><text x="40" y="80" font-family="Segoe UI" font-size="16" fill="'+C.secundario+'">Cuatro acabados · siluetas y ayudas reutilizables · muestras de los PNG reales</text>',W,H)),left:0,top:0});
 for(let row=0;row<finishes.length;row++) {
  const finish=finishes[row],y=120+row*230;
  tiles.push({input:Buffer.from(svg('<text x="0" y="24" font-family="Segoe UI" font-size="22" fill="'+C.grafito+'">'+finish.replaceAll('_',' ')+'</text>',350,32)),left:40,top:y});
  for(let col=0;col<12;col++) {
   const side=col<6?'blanca':'negra',role=Object.keys(shapes)[col%6];
   const theme=finish==='veta_fina'?'taller':finish==='mineral_suave'?'pizarra':'club';
   const sqSide=col%2?'oscura':'clara';
   const x=40+col*112,yy=y+44;
   const tile=await sharp(path.join(ROOT,resources['casilla.'+theme+'.'+finish+'.'+sqSide].png[120].archivo)).resize(100,100).composite([{input:await sharp(path.join(ROOT,resources['pieza.'+finish+'.'+side+'.'+role].png[120].archivo)).resize(100,100).toBuffer()}]).png().toBuffer();
   tiles.push({input:tile,left:x,top:yy});
   const ghost=await sharp(path.join(ROOT,resources['casilla.'+theme+'.'+finish+'.'+sqSide].png[60].archivo)).composite([{input:path.join(ROOT,resources['proyeccion.'+finish+'.'+side+'.'+role].png[60].archivo)}]).png().toBuffer();
   tiles.push({input:ghost,left:x+20,top:yy+108});
  }
 }
 const labels=['seleccion','foco','destino_legal','captura_legal','atencion','jaque','promocion_pendiente','ultima_jugada_origen','ultima_jugada_destino'];
 for(let i=0;i<labels.length;i++) {
  const x=40+i*145,y=1090;
  const tile=await sharp(path.join(ROOT,resources['casilla.club.liso_mate.'+(i%2?'oscura':'clara')].png[120].archivo)).composite([{input:path.join(ROOT,resources['marca.'+labels[i]].png[120].archivo)}]).png().toBuffer();
  tiles.push({input:tile,left:x,top:y});
 }
 tiles.push({input:path.join(ROOT,resources['flecha.ambar.continua'].png[120].archivo),left:40,top:1260});
 tiles.push({input:path.join(ROOT,resources['flecha.azul.discontinua'].png[120].archivo),left:440,top:1260});
 tiles.push({input:path.join(ROOT,resources['tipografia.muestra_titulo'].png[120].archivo),left:850,top:1260});
 await sharp({create:{width:W,height:H,channels:4,background:'#F3F1E8'}}).composite(tiles).png().toFile(path.join(ROOT,'VISTA_GENERAL.png'));
 // Validación de todos los PNG de recursos, medidas y transparencia.
 const checks={recursos:Object.keys(resources).length,png:0,svg:0,errores:[],sha256:{},tamanos:SIZES,transparencia_verificada:true,variacion_luminancia_casillas:{}};
 for(const [id,r] of Object.entries(resources)) {
  if(r.svg) checks.svg++;
  const files=r.png?Object.values(r.png):[{archivo:r.archivo,ancho:r.ancho,alto:r.alto}];
  for(const file of files) {
   const full=path.join(ROOT,file.archivo),buff=fs.readFileSync(full);
   const meta=await sharp(buff).metadata();
   checks.png++;
   if(meta.width!==file.ancho||meta.height!==file.alto) checks.errores.push(id+': dimensiones');
   const raw=await sharp(buff).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   if(r.tipo==='casilla') {
    const ref=lum(r.color_base.slice(1).match(/../g).map(x=>parseInt(x,16)));
    let delta=0;
    for(let i=0;i<raw.data.length;i+=4) delta=Math.max(delta,Math.abs(lum([raw.data[i],raw.data[i+1],raw.data[i+2]])-ref));
    checks.variacion_luminancia_casillas[file.archivo]=Number(delta.toFixed(6));
    if(delta>0.015) checks.errores.push(id+': textura excede presupuesto de luminancia');
   }
   if(['pieza','proyeccion'].includes(r.tipo)) {
    let visible=0,clear=0;
    for(let i=3;i<raw.data.length;i+=4){if(raw.data[i]>0)visible++;else clear++;}
    if(!visible||!clear||raw.data[3]!==0) checks.errores.push(id+': transparencia o contenido');
   }
   checks.sha256[file.archivo]=crypto.createHash('sha256').update(buff).digest('hex');
  }
 }
 put('VALIDACION.json',JSON.stringify(checks,null,2)+'\n');
 console.log(JSON.stringify({recursos:checks.recursos,png:checks.png,svg:checks.svg,errores:checks.errores,paquete:ROOT}));
}
build().catch(e=>{console.error(e);process.exit(1);});
