<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { Mill, UtilizationResponse, Workshop } from '../lib/types';

  const WINDOWS = [7, 14, 30];

  let days = 7;
  let millFilter = '';
  let data: UtilizationResponse | null = null;
  let mills: Mill[] = [];
  let workshops: Workshop[] = [];
  let error = '';
  let loading = true;

  async function load() {
    loading = true;
    error = '';
    const qs = new URLSearchParams({ days: String(days) });
    if (millFilter) qs.set('millId', millFilter);
    try {
      data = await api<UtilizationResponse>(`/utilization?${qs.toString()}`);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    try {
      [mills, workshops] = await Promise.all([
        api<Mill[]>('/mills'),
        api<Workshop[]>('/workshops'),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : '基础数据加载失败';
    }
    await load();
  });

  function workshopName(id: number): string {
    return workshops.find((w) => w.id === id)?.name ?? `#${id}`;
  }

  function pct(ratio: number): string {
    // 后端已封顶到 1，这里只做展示换算
    return `${(ratio * 100).toFixed(1)}%`;
  }

  function fmtMin(min: number): string {
    return min.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  }

  function switchDays(d: number) {
    days = d;
    load();
  }

  function onMillChange(e: Event) {
    millFilter = (e.target as HTMLSelectElement).value;
    load();
  }
</script>

<header class="page-head">
  <h1>研磨机利用率</h1>
  <p>按研磨遍次实际时长聚合，利用率 = 窗口内研磨分钟 ÷（天数 × 8 小时 × 60），封顶 100%</p>
</header>

<section class="panel">
  <div class="controls">
    <div class="seg">
      <span class="ctrl-label">窗口</span>
      {#each WINDOWS as d}
        <button class:active={days === d} on:click={() => switchDays(d)}>近 {d} 天</button>
      {/each}
    </div>
    <label class="mill-pick">研磨机
      <select value={millFilter} on:change={onMillChange}>
        <option value="">全部机台</option>
        {#each mills as m}
          <option value={String(m.id)}>{m.millCode}</option>
        {/each}
      </select>
    </label>
  </div>
</section>

{#if error}
  <div class="err">{error}</div>
{/if}

{#if loading}
  <div class="muted">加载中…</div>
{:else if data}
  <section class="panel">
    <div class="basis muted">
      单机理论满负荷 {fmtMin(data.theoreticalMinutesPerMill)} 分钟 / {data.days} 天（按每天 8 小时计）
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>研磨机</th>
          <th>车间</th>
          <th>研磨分钟</th>
          <th>遍次数</th>
          <th>利用率</th>
          <th class="bar-col">负荷条形</th>
        </tr>
      </thead>
      <tbody>
        {#each data.items as item}
          <tr>
            <td>{item.millCode}</td>
            <td>{workshopName(item.workshopId)}</td>
            <td>{fmtMin(item.totalMinutes)}</td>
            <td>{item.passCount}</td>
            <td class="ratio">{pct(item.utilizationRatio)}</td>
            <td class="bar-col">
              <div class="bar-track">
                <div class="bar-fill" style={`width:${pct(item.utilizationRatio)}`}></div>
              </div>
            </td>
          </tr>
        {:else}
          <tr><td colspan="6">窗口内暂无研磨遍次</td></tr>
        {/each}
      </tbody>
    </table>
  </section>
{/if}

<style>
  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .seg {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .ctrl-label {
    color: var(--steel);
    font-size: 0.85rem;
    margin-right: 0.3rem;
  }

  .seg button {
    border: 1px solid var(--line);
    background: transparent;
    color: var(--steel);
    padding: 0.4rem 0.8rem;
    cursor: pointer;
  }

  .seg button:hover {
    border-color: var(--vermillion-700);
    color: white;
  }

  .seg button.active {
    border-color: var(--vermillion-700);
    background: linear-gradient(90deg, rgba(139, 37, 0, 0.35), rgba(192, 57, 43, 0.12));
    color: white;
  }

  .mill-pick {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.85rem;
    color: var(--steel);
  }

  .mill-pick select {
    border: 1px solid var(--line);
    background: rgba(0, 0, 0, 0.35);
    color: white;
    padding: 0.45rem 0.6rem;
  }

  .basis {
    font-size: 0.82rem;
    margin-bottom: 0.8rem;
  }

  .ratio {
    font-family: var(--font-display);
    color: var(--vermillion-400);
    white-space: nowrap;
  }

  .bar-col {
    width: 32%;
    min-width: 160px;
  }

  .bar-track {
    height: 14px;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid var(--line);
  }

  .bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--vermillion-900), var(--vermillion-500));
    transition: width 0.25s ease;
  }
</style>
