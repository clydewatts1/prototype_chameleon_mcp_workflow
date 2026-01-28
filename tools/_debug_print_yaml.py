import yaml
p='examples/minimum/constitutional_zero_agent.yaml'
with open(p) as f:
    d=yaml.safe_load(f)
print('WORKFLOW_NAME:', d.get('workflow',{}).get('name'))
print('ROLES:')
for r in d.get('roles',[]):
    print('  -', r)
print('COMPONENTS:')
for c in d.get('components',[]):
    print('  -', c)
print('GUARDIANS TOP-LEVEL:', d.get('guardians'))
