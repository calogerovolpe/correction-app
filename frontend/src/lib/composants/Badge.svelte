<script lang="ts">
  type Variante = 'neutre' | 'info' | 'success' | 'attention' | 'danger';

  interface Props {
    texte: string;
    variante?: Variante;
  }

  let { texte, variante = 'neutre' }: Props = $props();
</script>

<span class="badge badge--{variante}">{texte}</span>

<style>
  .badge {
    display: inline-block;
    font-size: 0.8rem;
    line-height: 1.2;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    border: 1px solid currentColor;
    white-space: nowrap;
  }
  .badge--neutre {
    color: var(--encre-douce);
    background: var(--fond-surface);
  }
  .badge--info {
    color: var(--corr-style-texte);
    background: var(--corr-style-fond);
  }
  .badge--success {
    color: var(--succes);
    background: var(--corr-embellissement-fond);
  }
  .badge--attention {
    color: var(--attention);
    background: #fff8e1;
  }
  .badge--danger {
    color: var(--erreur);
    background: var(--corr-forme-fond);
  }
</style>