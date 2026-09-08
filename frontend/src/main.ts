import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';

const cible = document.getElementById('app');
if (!cible) {
  throw new Error('Élément #app introuvable dans index.html');
}

mount(App, { target: cible });