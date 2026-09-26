import { useEffect, useRef } from 'react';
// Importar Chart.js com auto-registration para garantir que tudo está registrado
import { Chart, registerables } from 'chart.js';
import type { PlayersChartDataResponse } from '@/services/reports';

// Registrar todos os componentes automaticamente
Chart.register(...registerables);

interface PlayersChartProps {
  data: NonNullable<PlayersChartDataResponse['data']>;
}

export function PlayersChart({ data }: PlayersChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<Chart<'line'> | null>(null);
  const isMountedRef = useRef(true);

  // Configurar cores do tema SCUM
  const lineColor = '#f97316'; // scum-orange
  const fillColor = 'rgba(249, 115, 22, 0.2)';

  useEffect(() => {
    isMountedRef.current = true;
    
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    
    // Função helper para destruir gráfico de forma segura
    const destroyChart = (chart: Chart | null) => {
      if (!chart) return;
      try {
        chart.destroy();
      } catch (error) {
        // Ignorar erros ao destruir
      }
    };

    // Verificar e destruir gráfico existente no canvas
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
      destroyChart(existingChart);
    }

    // Destruir gráfico anterior da ref
    if (chartInstanceRef.current) {
      destroyChart(chartInstanceRef.current);
      chartInstanceRef.current = null;
    }

    // Pequeno delay para garantir que o canvas está limpo
    const timeoutId = setTimeout(() => {
      if (!isMountedRef.current || !canvasRef.current) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const chartData = {
        labels: data.labels,
        datasets: [
          {
            label: data.datasets[0].label,
            data: data.datasets[0].data,
            borderColor: lineColor,
            backgroundColor: fillColor,
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: lineColor,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
          },
        ],
      };

      const config = {
        type: 'line' as const,
        data: chartData,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index' as const,
          },
          plugins: {
            legend: {
              display: true,
              position: 'top' as const,
              labels: {
                color: 'rgba(255, 255, 255, 0.8)',
                font: {
                  size: 12,
                },
              },
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
              titleColor: 'rgba(255, 255, 255, 0.9)',
              bodyColor: 'rgba(255, 255, 255, 0.8)',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              borderWidth: 1,
              padding: 12,
              callbacks: {
                label: function(context: any) {
                  return `${context.parsed.y.toFixed(1)} jogadores`;
                },
              },
            },
          },
          scales: {
            x: {
              ticks: {
                color: 'rgba(255, 255, 255, 0.6)',
                font: {
                  size: 12,
                },
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)',
              },
            },
            y: {
              beginAtZero: true,
              ticks: {
                color: 'rgba(255, 255, 255, 0.6)',
                font: {
                  size: 12,
                },
                stepSize: 1,
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)',
              },
              title: {
                display: true,
                text: 'Jogadores Online',
                color: 'rgba(255, 255, 255, 0.6)',
                font: {
                  size: 12,
                },
              },
            },
          },
        },
      };

      // Criar novo gráfico
      try {
        if (isMountedRef.current && canvasRef.current) {
          chartInstanceRef.current = new Chart(ctx, config);
        }
      } catch (error) {
        console.error('[PlayersChart] Erro ao criar gráfico:', error);
      }
    }, 50); // Pequeno delay para garantir limpeza

    // Cleanup
    return () => {
      isMountedRef.current = false;
      clearTimeout(timeoutId);
      
      if (chartInstanceRef.current) {
        destroyChart(chartInstanceRef.current);
        chartInstanceRef.current = null;
      }
      
      const chartToDestroy = Chart.getChart(canvas);
      if (chartToDestroy) {
        destroyChart(chartToDestroy);
      }
    };
  }, [data, lineColor, fillColor]);

  return (
    <div style={{ height: '400px', width: '100%', position: 'relative' }}>
      <canvas ref={canvasRef} />
    </div>
  );
}
