<template>
  <div class="min-vh-100 bg-light">
    <nav class="navbar navbar-expand-lg bg-white border-bottom">
      <div class="container-fluid px-4">
        <router-link class="navbar-brand fw-bold" to="/">ShuleLink</router-link>
        <span class="text-muted small">School Management Platform</span>
      </div>
    </nav>
    <main class="container-fluid px-4 py-4">
      <router-view />
    </main>
  </div>
</template>
