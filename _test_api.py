import urllib.request, json, sys
sys.stdout = open("_test_output.txt", "w")

print("Step 1: Building request...")

body = json.dumps({
    "filters": [{
        "criteria": [
            {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
            {"filterType": 10, "value": "python"},
        ],
        "pageNumber": 1,
        "pageSize": 5,
        "sortBy": 0,
        "sortOrder": 0,
    }],
    "assetTypes": [],
    "flags": 914,
}).encode("utf-8")

print("Step 2: Sending request...")

req = urllib.request.Request(
    "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
    data=body,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json;api-version=6.0-preview.1",
    },
)

try:
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode()
    print(f"Step 3: Got response, length={len(raw)}")
    
    data = json.loads(raw)
    exts = data.get("results", [{}])[0].get("extensions", [])
    print(f"Step 4: Got {len(exts)} extensions")
    
    for e in exts:
        pub = e.get("publisher", {}).get("publisherName", "")
        name = e.get("extensionName", "")
        dn = e.get("displayName", name)
        cats = e.get("categories", [])
        version = ""
        versions = e.get("versions", [])
        if versions:
            version = versions[0].get("version", "")
        
        dl = f"https://{pub}.gallery.vsassets.io/_apis/public/gallery/publisher/{pub}/extension/{name}/{version}/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"
        
        print(f"\n  {pub}.{name} v{version}")
        print(f"    Display: {dn}")
        print(f"    Categories: {cats}")
        print(f"    Download URL: {dl}")

except Exception as ex:
    print(f"ERROR: {ex}")

print("\nDone.")
sys.stdout.close()
