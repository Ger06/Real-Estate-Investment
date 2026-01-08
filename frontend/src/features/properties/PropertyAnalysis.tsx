/**
 * Property Analysis Page - Export table for investment analysis
 */
import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  Chip,
  Stack,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  FileDownload as FileDownloadIcon,
  TableChart as TableChartIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { propertiesApi, type Property } from '../../api/properties';
import * as XLSX from 'xlsx';

export default function PropertyAnalysis() {
  const navigate = useNavigate();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await propertiesApi.listProperties(0, 1000);
      setProperties(response.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar propiedades');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return `${currency} ${amount.toLocaleString('es-AR')}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-AR');
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      active: 'Disponible',
      sold: 'Vendido',
      rented: 'Alquilado',
      reserved: 'Reservado',
      removed: 'Removido',
    };
    return labels[status] || status;
  };

  const getConditionLabel = (condition?: string) => {
    if (!condition) return '-';
    const labels: Record<string, string> = {
      nuevo: 'Nuevo',
      a_estrenar: 'A Estrenar',
      buen_estado: 'Buen Estado',
      a_refaccionar: 'A Refaccionar',
      en_construccion: 'En Construcción',
      excelente: 'Excelente',
    };
    return labels[condition] || condition;
  };

  // Exportar a Excel
  const exportToExcel = () => {
    const data = properties.map((property) => ({
      'Dirección - Calle': property.street || '-',
      'Dirección - Altura': property.street_number || '-',
      'Dirección - Barrio': property.neighborhood || '-',
      'Dirección Completa': property.address || '-',
      Ciudad: property.city,
      Estado: getConditionLabel(property.property_condition),
      'Sup. Cubierta (m²)': property.covered_area || '-',
      'Sup. Semi Cubierta (m²)': property.semi_covered_area || '-',
      'Sup. Descubierta (m²)': property.uncovered_area || '-',
      'Sup. Total (m²)': property.total_area || '-',
      'Valor Estimado': property.estimated_value
        ? formatCurrency(property.estimated_value, property.currency)
        : '-',
      'Fecha Actualización': formatDate(property.updated_at || property.created_at),
      Precio: formatCurrency(property.price, property.currency),
      'Precio/m²': property.price_per_sqm
        ? formatCurrency(property.price_per_sqm, property.currency)
        : '-',
      'Estado Venta': getStatusLabel(property.status),
      Observaciones: property.observations || '-',
      'Link Publicación': property.source_url || '-',
      Fuente: property.source,
      Tipo: property.property_type,
      'Tipo Operación': property.operation_type,
      Dormitorios: property.bedrooms || '-',
      Baños: property.bathrooms || '-',
      Cocheras: property.parking_spaces || '-',
    }));

    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Análisis Propiedades');

    // Adjust column widths
    const maxWidth = 50;
    const wscols = Object.keys(data[0] || {}).map(() => ({ wch: maxWidth }));
    worksheet['!cols'] = wscols;

    XLSX.writeFile(workbook, `analisis_propiedades_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  // Exportar a CSV
  const exportToCSV = () => {
    const data = properties.map((property) => ({
      'Dirección - Calle': property.street || '-',
      'Dirección - Altura': property.street_number || '-',
      'Dirección - Barrio': property.neighborhood || '-',
      'Dirección Completa': property.address || '-',
      Ciudad: property.city,
      Estado: getConditionLabel(property.property_condition),
      'Sup. Cubierta (m²)': property.covered_area || '-',
      'Sup. Semi Cubierta (m²)': property.semi_covered_area || '-',
      'Sup. Descubierta (m²)': property.uncovered_area || '-',
      'Sup. Total (m²)': property.total_area || '-',
      'Valor Estimado': property.estimated_value
        ? formatCurrency(property.estimated_value, property.currency)
        : '-',
      'Fecha Actualización': formatDate(property.updated_at || property.created_at),
      Precio: formatCurrency(property.price, property.currency),
      'Precio/m²': property.price_per_sqm
        ? formatCurrency(property.price_per_sqm, property.currency)
        : '-',
      'Estado Venta': getStatusLabel(property.status),
      Observaciones: property.observations || '-',
      'Link Publicación': property.source_url || '-',
    }));

    const worksheet = XLSX.utils.json_to_sheet(data);
    const csv = XLSX.utils.sheet_to_csv(worksheet);

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `analisis_propiedades_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/properties')}
            sx={{ mb: 1 }}
          >
            Volver a Propiedades
          </Button>
          <Typography variant="h4">Análisis de Propiedades</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Tabla exportable para análisis de desarrollo inmobiliario ({properties.length}{' '}
            propiedades)
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={exportToCSV}>
            Exportar CSV
          </Button>
          <Button variant="contained" startIcon={<TableChartIcon />} onClick={exportToExcel}>
            Exportar Excel
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Table */}
      <TableContainer component={Paper} sx={{ maxHeight: 'calc(100vh - 250px)' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Imagen
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Calle
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Altura
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Barrio
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Estado
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Sup. Cub.
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Sup. Semi
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Sup. Desc.
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Sup. Total
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Valor Estimado
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Fecha Act.
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Precio
              </TableCell>
              <TableCell
                sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}
                align="right"
              >
                Precio/m²
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Estado Venta
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Observaciones
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', bgcolor: 'primary.main', color: 'white' }}>
                Link
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {properties.map((property) => {
              const primaryImage = property.images?.find((img) => img.is_primary) || property.images?.[0];

              return (
                <TableRow key={property.id} hover>
                  <TableCell>
                    <Avatar
                      src={primaryImage?.url}
                      variant="rounded"
                      sx={{ width: 60, height: 60 }}
                    >
                      🏠
                    </Avatar>
                  </TableCell>
                  <TableCell>{property.street || '-'}</TableCell>
                  <TableCell>{property.street_number || '-'}</TableCell>
                  <TableCell>{property.neighborhood || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={getConditionLabel(property.property_condition)}
                      size="small"
                      color={property.property_condition === 'a_estrenar' ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="right">{property.covered_area || '-'}</TableCell>
                  <TableCell align="right">{property.semi_covered_area || '-'}</TableCell>
                  <TableCell align="right">{property.uncovered_area || '-'}</TableCell>
                  <TableCell align="right">
                    <strong>{property.total_area || '-'}</strong>
                  </TableCell>
                  <TableCell align="right">
                    {property.estimated_value
                      ? formatCurrency(property.estimated_value, property.currency)
                      : '-'}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {formatDate(property.updated_at || property.created_at)}
                  </TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <strong>{formatCurrency(property.price, property.currency)}</strong>
                  </TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    {property.price_per_sqm
                      ? formatCurrency(property.price_per_sqm, property.currency)
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusLabel(property.status)}
                      size="small"
                      color={
                        property.status === 'active'
                          ? 'success'
                          : property.status === 'sold'
                          ? 'error'
                          : property.status === 'reserved'
                          ? 'warning'
                          : 'default'
                      }
                    />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {property.observations || '-'}
                  </TableCell>
                  <TableCell>
                    {property.source_url ? (
                      <Button
                        size="small"
                        variant="text"
                        href={property.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Ver
                      </Button>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {properties.length === 0 && !loading && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="body1" color="text.secondary" align="center">
            No hay propiedades para analizar.
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
