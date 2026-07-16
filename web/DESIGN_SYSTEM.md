# nexTalent Design System

El sistema visual prioriza claridad, confianza y calma: la interfaz debe ayudar a tomar decisiones profesionales sin parecer un panel técnico ni exagerar la certeza de la IA.

## Fundamentos

- **Tipografía:** Playfair Display para narrativa y jerarquía; DM Sans para interfaz; JetBrains Mono solo para identificadores y datos técnicos.
- **Color:** terracota para acción y énfasis, negro cálido para estructura, verdes apagados para progreso confirmado y fondos marfil para reducir fatiga.
- **Espaciado:** ritmo basado en 4 px, con superficies de 16–24 px y separación de secciones de 24–36 px.
- **Radios:** 8 px para controles, 12 px para campos y 16 px para superficies principales.
- **Sombras:** se reservan para elementos elevados o interactivos; la jerarquía ordinaria se construye con espacio y contraste.
- **Movimiento:** breve y funcional, siempre compatible con `prefers-reduced-motion`.

## Tokens

Los tokens viven en `src/index.css`. No se deben introducir colores hexadecimales, sombras o radios nuevos dentro de páginas salvo que representen datos dinámicos.

Grupos principales:

- Superficies: `--parchment`, `--ivory`, `--surface-subtle`.
- Texto: `--near-black`, `--charcoal-warm`, `--olive-gray`, `--stone-gray`.
- Semánticos: `--terracotta`, `--success`, `--warning`, `--error-crimson`.
- Forma: `--radius-sm` a `--radius-xl`.
- Elevación: `--shadow-sm`, `--shadow-md`.

## Componentes base

- `Button`: acciones primarias, secundarias, oscuras, outline y ghost.
- `Card`: superficies por defecto, sutiles u oscuras.
- `Badge`: metadatos, categorías y estados breves.
- `Field`: etiqueta, control y texto de ayuda.
- `ProgressBar`: cobertura o progreso con valor accesible.
- `PageHeader`: cabecera consistente de cada herramienta.
- `StatusMessage`: error, información o confirmación.

Los componentes de dominio viven fuera de `components/ui`: `jobs`, `career` e `insights`. Las páginas deben conservar la carga de datos y el estado de navegación, delegando la presentación en dichos componentes.

## Criterios de uso

1. Una página debe tener una sola acción primaria visible por sección.
2. El terracota no se usa como decoración indiscriminada.
3. Un porcentaje siempre debe indicar qué mide y sobre qué muestra.
4. Los estados ambiguos no usan el mismo tratamiento que los confirmados.
5. Toda información representada mediante color debe tener también texto o icono.
6. Los controles mantienen un área táctil mínima de 40 px.
7. Antes de crear un nuevo patrón se comprueba si puede componerse con los primitivos existentes.
