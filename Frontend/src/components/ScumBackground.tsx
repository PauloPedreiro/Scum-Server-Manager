import React from 'react';
import { motion } from 'framer-motion';

// Imagem oficial do SCUM salva localmente
const scumImages = [
  '/images/scum-bg.jpg',
  // Outras imagens podem ser adicionadas aqui se desejar alternar backgrounds
];

interface ScumBackgroundProps {
  children: React.ReactNode;
  imageIndex?: number;
}

const ScumBackground: React.FC<ScumBackgroundProps> = ({ children, imageIndex = 0 }) => {
  const currentImage = scumImages[imageIndex % scumImages.length];

  return (
    <div className="min-h-screen relative overflow-hidden w-full">
      {/* Background com imagem do SCUM */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `url('${currentImage}')`,
        }}
      >
        {/* Overlay escuro para melhorar legibilidade */}
        <div className="absolute inset-0 bg-black/70"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-scum-primary/30 via-scum-dark/80 to-scum-gray/40"></div>
      </div>
      
      {/* Efeitos de luz e partículas */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-scum-accent/20 rounded-full blur-3xl animate-pulse-slow"></div>
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-scum-secondary/20 rounded-full blur-3xl animate-pulse-slow delay-1000"></div>
      
      {/* Partículas flutuantes */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-scum-accent/30 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              y: [0, -20, 0],
              opacity: [0.3, 0.8, 0.3],
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      {/* Conteúdo */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

export default ScumBackground; 