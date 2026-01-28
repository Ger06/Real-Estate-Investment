import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  FormGroup,
  FormLabel,
  FormHelperText,
  Grid,
  Typography,
  Divider,
  Box,
} from '@mui/material';
import type { SavedSearch } from '../../api/savedSearches';

const PORTALS = [
  { value: 'argenprop', label: 'Argenprop' },
  { value: 'zonaprop', label: 'Zonaprop' },
  { value: 'remax', label: 'Remax' },
  { value: 'mercadolibre', label: 'MercadoLibre' },
];

const OPERATION_TYPES = [
  { value: 'venta', label: 'Venta' },
  { value: 'alquiler', label: 'Alquiler' },
  { value: 'alquiler_temporal', label: 'Alquiler Temporal' },
];

const PROPERTY_TYPES = [
  { value: '', label: 'Todos' },
  { value: 'departamento', label: 'Departamento' },
  { value: 'casa', label: 'Casa' },
  { value: 'ph', label: 'PH' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'local', label: 'Local' },
  { value: 'oficina', label: 'Oficina' },
];

const CURRENCIES = [
  { value: 'USD', label: 'USD' },
  { value: 'ARS', label: 'ARS' },
];

const schema = z.object({
  name: z.string().min(1, 'El nombre es requerido').max(255),
  description: z.string().optional(),
  portals: z.array(z.string()).min(1, 'Seleccione al menos un portal'),
  operation_type: z.string().min(1, 'Seleccione tipo de operación'),
  property_type: z.string().optional(),
  city: z.string().optional(),
  province: z.string().optional(),
  neighborhoods_text: z.string().optional(),
  currency: z.string().default('USD'),
  min_price: z.coerce.number().positive().optional().or(z.literal('')),
  max_price: z.coerce.number().positive().optional().or(z.literal('')),
  min_area: z.coerce.number().positive().optional().or(z.literal('')),
  max_area: z.coerce.number().positive().optional().or(z.literal('')),
  min_bedrooms: z.coerce.number().int().min(0).optional().or(z.literal('')),
  max_bedrooms: z.coerce.number().int().min(0).optional().or(z.literal('')),
  min_bathrooms: z.coerce.number().int().min(0).optional().or(z.literal('')),
  auto_scrape: z.boolean().default(false),
  is_active: z.boolean().default(true),
});

type FormValues = z.infer<typeof schema>;

interface SavedSearchFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, unknown>) => void;
  search?: SavedSearch | null;
  loading?: boolean;
}

export default function SavedSearchForm({ open, onClose, onSubmit, search, loading }: SavedSearchFormProps) {
  const isEdit = !!search;

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      description: '',
      portals: [],
      operation_type: 'venta',
      property_type: '',
      city: '',
      province: '',
      neighborhoods_text: '',
      currency: 'USD',
      min_price: '',
      max_price: '',
      min_area: '',
      max_area: '',
      min_bedrooms: '',
      max_bedrooms: '',
      min_bathrooms: '',
      auto_scrape: false,
      is_active: true,
    },
  });

  useEffect(() => {
    if (open) {
      if (search) {
        reset({
          name: search.name,
          description: search.description || '',
          portals: search.portals,
          operation_type: search.operation_type,
          property_type: search.property_type || '',
          city: search.city || '',
          province: search.province || '',
          neighborhoods_text: search.neighborhoods?.join(', ') || '',
          currency: search.currency || 'USD',
          min_price: search.min_price ?? '',
          max_price: search.max_price ?? '',
          min_area: search.min_area ?? '',
          max_area: search.max_area ?? '',
          min_bedrooms: search.min_bedrooms ?? '',
          max_bedrooms: search.max_bedrooms ?? '',
          min_bathrooms: search.min_bathrooms ?? '',
          auto_scrape: search.auto_scrape,
          is_active: search.is_active,
        });
      } else {
        reset({
          name: '',
          description: '',
          portals: [],
          operation_type: 'venta',
          property_type: '',
          city: '',
          province: '',
          neighborhoods_text: '',
          currency: 'USD',
          min_price: '',
          max_price: '',
          min_area: '',
          max_area: '',
          min_bedrooms: '',
          max_bedrooms: '',
          min_bathrooms: '',
          auto_scrape: false,
          is_active: true,
        });
      }
    }
  }, [open, search, reset]);

  const handleFormSubmit = (values: FormValues) => {
    const neighborhoods = values.neighborhoods_text
      ? values.neighborhoods_text.split(',').map((n) => n.trim()).filter(Boolean)
      : undefined;

    const data: Record<string, unknown> = {
      name: values.name,
      portals: values.portals,
      operation_type: values.operation_type,
      currency: values.currency,
      auto_scrape: values.auto_scrape,
      is_active: values.is_active,
    };

    if (values.description) data.description = values.description;
    if (values.property_type) data.property_type = values.property_type;
    if (values.city) data.city = values.city;
    if (values.province) data.province = values.province;
    if (neighborhoods && neighborhoods.length > 0) data.neighborhoods = neighborhoods;
    if (values.min_price !== '' && values.min_price !== undefined) data.min_price = Number(values.min_price);
    if (values.max_price !== '' && values.max_price !== undefined) data.max_price = Number(values.max_price);
    if (values.min_area !== '' && values.min_area !== undefined) data.min_area = Number(values.min_area);
    if (values.max_area !== '' && values.max_area !== undefined) data.max_area = Number(values.max_area);
    if (values.min_bedrooms !== '' && values.min_bedrooms !== undefined) data.min_bedrooms = Number(values.min_bedrooms);
    if (values.max_bedrooms !== '' && values.max_bedrooms !== undefined) data.max_bedrooms = Number(values.max_bedrooms);
    if (values.min_bathrooms !== '' && values.min_bathrooms !== undefined) data.min_bathrooms = Number(values.min_bathrooms);

    onSubmit(data);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{isEdit ? 'Editar Búsqueda' : 'Nueva Búsqueda'}</DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent dividers>
          {/* Información Básica */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Información Básica
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Controller
                name="name"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Nombre"
                    fullWidth
                    required
                    error={!!errors.name}
                    helperText={errors.name?.message}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Descripción"
                    fullWidth
                    multiline
                    rows={2}
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Portales */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Portales
          </Typography>
          <Controller
            name="portals"
            control={control}
            render={({ field }) => (
              <FormControl error={!!errors.portals} component="fieldset" sx={{ mb: 3 }}>
                <FormLabel component="legend">Seleccione los portales a buscar</FormLabel>
                <FormGroup row>
                  {PORTALS.map((portal) => (
                    <FormControlLabel
                      key={portal.value}
                      control={
                        <Checkbox
                          checked={field.value.includes(portal.value)}
                          onChange={(e) => {
                            const newValue = e.target.checked
                              ? [...field.value, portal.value]
                              : field.value.filter((v: string) => v !== portal.value);
                            field.onChange(newValue);
                          }}
                        />
                      }
                      label={portal.label}
                    />
                  ))}
                </FormGroup>
                {errors.portals && (
                  <FormHelperText>{errors.portals.message}</FormHelperText>
                )}
              </FormControl>
            )}
          />

          <Divider sx={{ mb: 2 }} />

          {/* Filtros de Propiedad */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Filtros de Propiedad
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="operation_type"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth required error={!!errors.operation_type}>
                    <InputLabel>Tipo de Operación</InputLabel>
                    <Select {...field} label="Tipo de Operación">
                      {OPERATION_TYPES.map((op) => (
                        <MenuItem key={op.value} value={op.value}>{op.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="property_type"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Tipo de Propiedad</InputLabel>
                    <Select {...field} label="Tipo de Propiedad">
                      {PROPERTY_TYPES.map((pt) => (
                        <MenuItem key={pt.value} value={pt.value}>{pt.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Ubicación */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Ubicación
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="city"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Ciudad" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="province"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Provincia" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="neighborhoods_text"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Barrios"
                    fullWidth
                    helperText="Separados por coma (ej: Palermo, Belgrano, Recoleta)"
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Precio */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Precio
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={4}>
              <Controller
                name="currency"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Moneda</InputLabel>
                    <Select {...field} label="Moneda">
                      {CURRENCIES.map((c) => (
                        <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="min_price"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Precio Mínimo"
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="max_price"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Precio Máximo"
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Superficie */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Superficie
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="min_area"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Superficie Mínima (m²)"
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="max_area"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Superficie Máxima (m²)"
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Ambientes */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Ambientes
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={4}>
              <Controller
                name="min_bedrooms"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Dormitorios Mín."
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="max_bedrooms"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Dormitorios Máx."
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="min_bathrooms"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Baños Mín."
                    type="number"
                    fullWidth
                    inputProps={{ min: 0 }}
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 2 }} />

          {/* Opciones */}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Opciones
          </Typography>
          <Box sx={{ mb: 1 }}>
            <Controller
              name="auto_scrape"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox checked={field.value} onChange={field.onChange} />}
                  label="Auto-scrapear propiedades encontradas"
                />
              )}
            />
          </Box>
          <Box>
            <Controller
              name="is_active"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox checked={field.value} onChange={field.onChange} />}
                  label="Búsqueda activa"
                />
              )}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {isEdit ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
