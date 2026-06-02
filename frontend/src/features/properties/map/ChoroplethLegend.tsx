/**
 * Legend overlay for the choropleth map
 */
import { Box, Typography } from '@mui/material';
import type { ColorScaleBreakpoint } from '../../../api/properties';

interface Props {
  colorScale: ColorScaleBreakpoint[];
}

export default function ChoroplethLegend({ colorScale }: Props) {
  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 30,
        left: 10,
        zIndex: 400,
        bgcolor: 'rgba(255,255,255,0.92)',
        borderRadius: 1,
        p: 1.5,
        boxShadow: 2,
        minWidth: 160,
      }}
    >
      <Typography variant="caption" fontWeight="bold" display="block" mb={0.5}>
        USD/m² (venta)
      </Typography>
      {colorScale.map((bp) => (
        <Box key={bp.level} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
          <Box
            sx={{
              width: 16,
              height: 16,
              borderRadius: 0.5,
              bgcolor: bp.color,
              border: '1px solid #aaa',
              flexShrink: 0,
            }}
          />
          <Typography variant="caption">{bp.label}</Typography>
        </Box>
      ))}
    </Box>
  );
}
