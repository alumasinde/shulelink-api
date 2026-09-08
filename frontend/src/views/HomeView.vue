<template>
  <section class="landing-page">
    <div class="container py-5">
      <div class="row align-items-center g-5 py-lg-5">
        <div class="col-lg-7">
          <span class="eyebrow">SCHOOL MANAGEMENT PLATFORM</span>
          <h1 class="display-4 fw-bold mt-3 mb-3">One connected workspace for every school.</h1>
          <p class="lead text-secondary mb-4">ShuleLink brings school operations into one secure, multi-tenant platform designed for modern Kenyan schools.</p>
          <div class="d-flex flex-wrap gap-2 mb-4"><span class="tech-pill">FastAPI</span><span class="tech-pill">Vue 3</span><span class="tech-pill">Bootstrap 5</span><span class="tech-pill">MySQL</span></div>
          <router-link to="/login" class="btn btn-primary btn-lg px-4">Sign in <i class="bi bi-arrow-right ms-2"></i></router-link>
        </div>
        <div class="col-lg-5"><div class="hero-card"><div class="hero-icon"><i class="bi bi-mortarboard-fill"></i></div><div class="h5 fw-bold mb-2">Built for school operations</div><p class="text-muted mb-4">Identity, tenant isolation and school administration are connected from the foundation up.</p><div class="feature-row"><i class="bi bi-shield-check"></i><span>Secure identity & access</span></div><div class="feature-row"><i class="bi bi-buildings"></i><span>Multi-school architecture</span></div><div class="feature-row"><i class="bi bi-diagram-3"></i><span>Modular platform design</span></div></div></div>
      </div>
    </div>
  </section>
</template>
