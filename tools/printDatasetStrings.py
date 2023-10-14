official_samples_used = [
  (1200, 300), (1200, 600), (1200, 800), (1200, 1000),
  (1500, 300), (1500, 600), (1500, 800), (1500, 1000), (1500, 1300),
  (2000, 300), (2000, 600), (2000, 900), (2000, 1100), (2000, 1300), (2000, 1600),
  (2500, 300), (2500, 600), (2500, 800), (2500, 1000), (2500, 1300), (2500, 1600), (2500, 1800),
  (3000, 300), (3000, 600), (3000, 800), (3000, 1000), (3000, 1300), (3000, 1600), (3000, 1800), (3000, 2600), (3000, 2800),
  (3500, 300), (3500, 600), (3500, 700), (3500, 1100), (3500, 1300), (3500, 1600), (3500, 2000), (3500, 2500), (3500, 2800),
  (4000, 300), (4000, 600), (4000, 800), (4000, 1000), (4000, 1300), (4000, 1600), (4000, 2000), (4000, 2200), (4000, 2500), (4000, 2800)
]

print('Total of {0} datasets used\n'.format(len(official_samples_used)))

dataset_strings = []

for (mX, mY) in official_samples_used:
    dataset_strings.append(f'XToYHTo6B_MX-{mX}_MY-{mY}')

print(' '.join(dataset_strings))
