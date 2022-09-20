#!/usr/bin/env python3

import requests
import json
from pathlib import Path
from datetime import datetime
import os
from pprint import pprint
import platform
import  getpass
import subprocess

def captureCommand (theCommand : str, timeout : int = 15):
    tmp = ""
    if isinstance(theCommand,list):
        theCommand = ' '.join(theCommand)
    # LOGGER.debug (theCommand)

    p = subprocess.Popen(theCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as te:
        print (str(te))
        p.kill()
        raise

    def fixTup (stdSomething):
        if not stdSomething:
            return None
        stdSomething = stdSomething.decode('utf-8').split('\n')
        stdSomething = [s for s in stdSomething if s]
        if len(stdSomething) == 0:
            return None
        elif len(stdSomething) == 1:
            return stdSomething[0]
        else:
            return stdSomething
    
    output = (fixTup(stdout)
             ,fixTup(stderr)
             ,theCommand
             )
        
    return output

def ensureWritable(theFile : Path):

    check = []
    theDir = theFile.parent

    if theFile.exists():
        check.append (theFile)

    createDir = False
    if theDir.is_dir():
        check.append (theDir)
    else:
        try:
            check.append (theDir.parent)
            createDir = True
        except:
            ...

    for c in check:
        if not os.access(c, os.W_OK):
            raise PermissionError (f"User '{getpass.getuser()}' has no permissions to write to '{c}'")

    if createDir:
        theDir.mkdir(exist_ok = True, parents = True)

def thisOne(theDict : dict) -> dict:

    outFile = Path(theDict['destination']).expanduser()
    ensureWritable (outFile)

    def _theFileTime (theFile):
        return datetime.fromtimestamp(theFile.stat().st_mtime).replace(microsecond=0).isoformat()

    def _now():
        return datetime.now().replace(microsecond=0).isoformat()

    try:
        response = requests.get(theDict['url'])
        theDict['status_code'] = response.status_code
        theDict['last_checked'] = _now()
        if response.ok:

            theDict['last_retrieved'] = _now()

            if 'retrieved_cnt' not in theDict:
                theDict['retrieved_cnt'] = 0

            theDict['retrieved_cnt'] = theDict['retrieved_cnt'] + 1
            if "replace" in theDict:
                # If we are doing a replace, assume we're talking about a text file
                content = response.text
                for r in theDict["replace"]:
                    content = content.replace(r["old"],r["new"])
                
                if not (outFile.is_file() and outFile.read_text() == content):
                    theDict['file_size']    = len(content)
                    outFile.write_text(content)

            else:
                # treat it as binary
                if outFile.is_file() and outFile.get_bytes() == response.content:
                    ...
                else:
                    outFile.write_bytes(response.content)
                    theDict['file_size'] = len(response.content)

            if "last_written" not in theDict:
                theDict['last_written'] = _theFileTime(outFile)

            if "chmod" in theDict:
                theChmod = theDict["chmod"]
                num = int(theChmod, 8)
                outFile.chmod(num)

        else:
           theDict.pop('file_size',None)
    finally:
        response.close()

    return theDict

def retrieveFromJSON(jsonFile : Path) -> list:

    links = json.loads(jsonFile.read_text())

    for ix,l in enumerate(links):
        links[ix] = thisOne(l)

    jsonFile.write_text(json.dumps(links, indent=2))

    return links

if __name__ == '__main__':
    jsonExt     = '.json'
    machineJSON = Path(__file__).parent.joinpath(f"_{platform.node()}{jsonExt}")
    
    if not machineJSON.is_file():
        defaultJSON = Path(__file__).with_suffix(jsonExt)
        machineJSON.write_text(defaultJSON.read_text())
        try:
            uid = captureCommand(['id','-u',os.getlogin()])[0]
            gid = captureCommand(['id','-g',uid])[0]
            captureCommand(['chown',f'{uid}:{gid}',str(machineJSON)])
        except:
            ...

    ensureWritable (machineJSON)

    retrieveFromJSON(machineJSON)
