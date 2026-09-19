<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { Mill, UtilizationReport } from '../lib/types';

  let report: UtilizationReport | null = null;
  let mills: Mill[] = [];
  let days = 7;
  let millId = '';
  let error = '';
  let loading = true;

  const dayOptions = [7, 14, 30];

  async function load() {
    error = '';
    loading = true;
    try {
      const qs = [`days=${days}`];
      if (millId) qs.push(`millId=${millId}`);
      report = await api<UtilizationReport>(`/utilization?${qs.join('&')}`);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    try {
      mills = await api<Mill[]>('/mills');
    } catch {
      // 机台筛选器留空,不阻塞看板
    }
    await load();
  });

  function pickDays(d: number) {
    days = d;
    load();
  }

  function pct(ratio: number): string {
    return (ratio * 100).toFixed(1);
  }
</script>

<header class="page-head">
  <h1>利用率看板</h1>
  <p>
    按研磨遍次时长聚合;满负荷口径:每机每天 {report?.shiftHoursPerDay ?? 8} 小时,利用率封顶 100%
  </p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel controls">
  <div class="seg">
    {#each dayOptions as d}
      <button class:active={days === d} on:click={() => pickDays(d)}>近 {d} 天</button>
    {/each}
  </div>
  <select bind:value={millId} on:change={load}>
    <option value="">全部研磨机</option>
    {#each mills as m}
      <option value={String(m.id)}>{m.millCode}</option>
    {/each}
  </select>
  {#if report}
    <span class="muted window">窗口:{report.windowStart} ~ {report.windowEnd}</span>
  {/if}
</section>

<section class="panel">
  {#if loading}
    <div class="muted">加载中…</div>
  {:else if report}
    <table class="data-table">
      <thead>
        <tr>
          <th>研磨机</th>
          <th>遍次数</th>
          <th>总分钟</th>
          <th>利用率</th>
          <th class="bar-col">负荷</th>
        </tr>
      </thead>
      <tbody>
        {#each report.items as item}
          <tr>
            <td>{item.millCode} <span class="muted">#{item.millId}</span></td>
            <td>{item.passCount}</td>
            <td>{item.totalMinutes}</td>
            <td>{pct(item.utilizationRatio)}%</td>
            <td class="bar-col">
              <div class="bar">
                <div class="fill" style="width: {pct(item.utilizationRatio)}%"></div>
              </div>
            </td>
          </tr>
        {:else}
          <tr><td colspan="5">暂无数据</td></tr>
        {/each}
      </tbody>
    </table>
  {/if}
</section>

<style>
  .controls {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    flex-wrap: wrap;
  }

  .seg {
    display: flex;
    gap: 0.35rem;
  }

  .seg button {
    border: 1px solid var(--line);
    background: transparent;
    color: var(--steel);
    padding: 0.45rem 0.9rem;
    cursor: pointer;
    border-radius: 2px;
    transition: 0.15s ease;
  }

  .seg button:hover {
    color: white;
    border-color: var(--vermillion-700);
  }

  .seg button.active {
    background: linear-gradient(90deg, var(--vermillion-900), var(--vermillion-700));
    border-color: var(--vermillion-700);
    color: white;
  }

  select {
    border: 1px solid var(--line);
    background: rgba(0, 0, 0, 0.35);
    color: white;
    padding: 0.45rem 0.65rem;
  }

  .window {
    font-size: 0.8rem;
  }

  .bar-col {
    width: 40%;
  }

  .bar {
    height: 12px;
    background: rgba(232, 228, 220, 0.08);
    border: 1px solid var(--line);
    overflow: hidden;
  }

  .fill {
    height: 100%;
    min-width: 2px;
    background: linear-gradient(90deg, var(--vermillion-900), var(--vermillion-500));
    transition: width 0.25s ease;
  }
</style>
