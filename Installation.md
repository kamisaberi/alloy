### How to use this now:
1. In your project's active workspace, create a folder named packages/ [2].
2. Put any recipe configuration YAML files inside it (e.g. packages/detectron2.yaml or packages/installer.yaml).
3. Run alloy update. This will automatically copy the files into your local user cache (~/.alloy/cache/recipes/) and generate the search index.
4. Now, both commands are operational offline:
alloy search <query> searches your local packages.
alloy install detectron2 will find ~/.alloy/cache/recipes/detectron2.yaml and install it entirely offline without calling any API [3].