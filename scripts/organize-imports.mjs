import fs from 'node:fs';
import path from 'node:path';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
const root=path.resolve('frontend');
const config=ts.readConfigFile(path.join(root,'tsconfig.json'),ts.sys.readFile);
const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,root);
const host={getScriptFileNames:()=>parsed.fileNames,getScriptVersion:()=> '0',getScriptSnapshot:name=>fs.existsSync(name)?ts.ScriptSnapshot.fromString(fs.readFileSync(name,'utf8')):undefined,getCurrentDirectory:()=>root,getCompilationSettings:()=>parsed.options,getDefaultLibFileName:options=>ts.getDefaultLibFilePath(options),fileExists:ts.sys.fileExists,readFile:ts.sys.readFile,readDirectory:ts.sys.readDirectory};
const service=ts.createLanguageService(host);
for(const file of parsed.fileNames){
  if(file.endsWith('.d.ts'))continue;
  const edits=service.organizeImports({type:'file',fileName:file},{},{});
  for(const edit of edits){let source=fs.readFileSync(edit.fileName,'utf8');for(const change of [...edit.textChanges].sort((a,b)=>b.span.start-a.span.start)){source=source.slice(0,change.span.start)+change.newText+source.slice(change.span.start+change.span.length)}fs.writeFileSync(edit.fileName,source)}
}
