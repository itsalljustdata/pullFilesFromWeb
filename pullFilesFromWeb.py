#!/usr/bin/env python3

import requests
import json
from pathlib import Path
from datetime import datetime
import os
from pprint import pprint

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
            raise PermissionError (f"User '{os.getlogin()}' has no permissions to write to '{c}'")

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
    retrieveFromJSON(Path(__file__).with_suffix('.json'))
