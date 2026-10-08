import {build} from 'esbuild';
import {execFileSync} from 'node:child_process';
import {mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
process.chdir(fileURLToPath(new URL('.',import.meta.url)));
mkdirSync('dist',{recursive:true});
await build({absWorkingDir:process.cwd(),entryPoints:['main.tsx'],outfile:'dist/viewer.js',bundle:true,minify:true,format:'iife',jsx:'automatic',alias:{'@':'./vendor','~':'./vendor'},define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof'});
execFileSync('node',['node_modules/@tailwindcss/cli/dist/index.mjs','-i','style.css','-o','dist/viewer.css','--minify'],{stdio:'inherit',env:{...process.env,RAYON_NUM_THREADS:'1'}});
