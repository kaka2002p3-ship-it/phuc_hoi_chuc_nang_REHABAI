# Đóng Góp Cho RehabAI

## Quy Tắc Phát Triển

### 1. Cấu Trúc Code
```
rehabai/
├── backend/          # FastAPI server
│   ├── api/          # API endpoints
│   ├── core/         # Core utilities (auth, db, config)
│   └── ml/           # ML inference
├── frontend/         # React app
├── training/         # PyTorch training
├── shared/           # Shared utilities
├── scripts/          # Utility scripts
└── tests/            # Test suite
```

### 2. Commit Message Format
```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore
Example: feat(inference): add confidence threshold
```

### 3. Pull Request Checklist
- [ ] Tests pass: `pytest`
- [ ] No new warnings
- [ ] Documentation updated
- [ ] Backup created in `backups/`

### 4. Database Changes
1. Tạo migration script trong `scripts/`
2. Backup database trước
3. Test trên copy database
4. Verify với `sqlite3`

## Liên Hệ
Email: contact@rehabai.local
