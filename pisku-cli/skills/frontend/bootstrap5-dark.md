# Bootstrap 5 + Dark Mode — Frontend Patterns

## Purpose
Context for building responsive UIs with Bootstrap 5. Use when project involves HTML/CSS layouts, component styling, dark mode, or glassmorphism effects.

## Bootstrap 5 Dark Mode
```html
<!-- Enable dark mode -->
<html lang="en" data-bs-theme="dark">
<head>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
```

## Glassmorphism Pattern
```css
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}
```

## Gradient Patterns
```css
:root {
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-cyan: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
}

.gradient-text {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.gradient-btn {
  background: var(--gradient-primary);
  border: none;
  transition: opacity 0.2s;
}
.gradient-btn:hover { opacity: 0.9; }
```

## Pricing Table Pattern
```html
<div class="row g-4 justify-content-center">
  <div class="col-md-5">
    <div class="card glass-card h-100">
      <div class="card-body p-4">
        <span class="badge bg-secondary mb-3">FREE</span>
        <h2 class="display-4 fw-bold">$0<small class="fs-5">/mo</small></h2>
        <ul class="list-unstyled mt-4">
          <li class="mb-2">✅ 10 skills</li>
          <li class="mb-2">✅ 1 project</li>
          <li class="mb-2 text-muted">❌ Advanced stats</li>
        </ul>
        <a href="#" class="btn btn-outline-light w-100 mt-auto">Download Free</a>
      </div>
    </div>
  </div>
  <div class="col-md-5">
    <div class="card glass-card h-100 border-primary">
      <div class="card-body p-4">
        <span class="badge bg-primary mb-3">PRO ⚡</span>
        <h2 class="display-4 fw-bold gradient-text">$5<small class="fs-5">/mo</small></h2>
        <ul class="list-unstyled mt-4">
          <li class="mb-2">✅ Unlimited skills</li>
          <li class="mb-2">✅ Unlimited projects</li>
          <li class="mb-2">✅ Dashboard + CSV export</li>
        </ul>
        <a href="#" class="btn gradient-btn text-white w-100 mt-auto">Go PRO</a>
      </div>
    </div>
  </div>
</div>
```

## Responsive Navbar
```html
<nav class="navbar navbar-expand-lg navbar-dark bg-transparent fixed-top">
  <div class="container">
    <a class="navbar-brand fw-bold gradient-text" href="#">PISKU</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="#features">Features</a></li>
        <li class="nav-item"><a class="nav-link" href="#pricing">Pricing</a></li>
      </ul>
    </div>
  </div>
</nav>
```

## Layout Utilities Cheat Sheet
- `d-flex align-items-center gap-3` — horizontal flex
- `py-5 px-4` — vertical/horizontal padding
- `text-center text-md-start` — responsive text align
- `order-md-2 order-1` — responsive column ordering
- `vh-100 d-flex align-items-center` — full-height hero
