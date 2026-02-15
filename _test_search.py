import urllib.request
import json

# Test 1: Can we reach Open VSX?
print("Testing Open VSX...")
try:
    url = "https://open-vsx.org/api/-/search?query=python&size=2"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        exts = data.get("extensions", [])
        print(f"  Open VSX OK: {len(exts)} results")
        for e in exts:
            print(f"    {e.get('namespace','')}.{e.get('name','')} - {e.get('displayName','')}")
except Exception as e:
    print(f"  Open VSX FAILED: {e}")

print()

# Test 2: Can we reach VS Code Marketplace?
print("Testing VS Code Marketplace...")
try:
    body = json.dumps({
        "filters": [{
            "criteria": [
                {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
                {"filterType": 10, "value": "python"},
            ],
            "pageNumber": 1,
            "pageSize": 2,
            "sortBy": 0,
            "sortOrder": 0,
        }],
        "assetTypes": [],
        "flags": 914,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json;api-version=6.0-preview.1",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        exts = data.get("results", [{}])[0].get("extensions", [])
        print(f"  Marketplace OK: {len(exts)} results")
        for e in exts:
            pub = e.get("publisher", {}).get("publisherName", "")
            name = e.get("extensionName", "")
            dn = e.get("displayName", name)
            print(f"    {pub}.{name} - {dn}")
except Exception as e:
    print(f"  Marketplace FAILED: {e}")

print("\nDone.")
