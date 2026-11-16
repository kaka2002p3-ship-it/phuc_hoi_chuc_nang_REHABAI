"""Analyze overfitting in training."""
import json

# Load training history
with open('experiments/optimized_seed7/fold_04_seed7/training_history.json', 'r') as f:
    history = json.load(f)

print('=== Training History Analysis (Seed 7 - Best Model) ===')
print()

# Find best epoch
best_idx = max(range(len(history['history'])), key=lambda i: history['history'][i]['val_f1'])
best_epoch = history['history'][best_idx]

print(f'Best Epoch: {best_epoch["epoch"]}')
print(f'  Train Accuracy: {best_epoch["train_accuracy"]:.4f}')
print(f'  Val Accuracy:   {best_epoch["val_accuracy"]:.4f}')
print(f'  Train F1:      {best_epoch["train_f1"]:.4f}')
print(f'  Val F1:        {best_epoch["val_f1"]:.4f}')
print()

# Gap analysis
gap_acc = best_epoch['train_accuracy'] - best_epoch['val_accuracy']
gap_f1 = best_epoch['train_f1'] - best_epoch['val_f1']

print('Overfitting Gap at Best Epoch:')
print(f'  Accuracy Gap: {gap_acc:.4f} ({gap_acc*100:.1f}%)')
print(f'  F1 Gap:      {gap_f1:.4f} ({gap_f1*100:.1f}%)')
print()

# Check all epochs
print('Full Training History:')
print('Epoch | Train Acc | Val Acc  | Gap     | Train F1 | Val F1  | Gap')
print('-' * 80)
for h in history['history']:
    gap = h['train_accuracy'] - h['val_accuracy']
    gap_f1_epoch = h['train_f1'] - h['val_f1']
    marker = ' <-- BEST' if h['epoch'] == best_epoch['epoch'] else ''
    print(f"  {h['epoch']:3d}  |   {h['train_accuracy']:.4f}  |  {h['val_accuracy']:.4f}  | {gap:.4f} |   {h['train_f1']:.4f}  |  {h['val_f1']:.4f}  | {gap_f1_epoch:.4f}{marker}")

print()
print('=' * 80)
print('CONCLUSION:')
if gap_acc > 0.15:
    print('  OVERFITTING DETECTED! Gap > 15%')
elif gap_acc > 0.05:
    print('  MILD OVERFITTING. Gap between 5-15%')
else:
    print('  MINIMAL OVERFITTING. Gap < 5%')
