export const CATALOGS = [
  {
    id: 'c1',
    file: 'Nordic_Kitchenware_Catalogue_2026.pdf',
    date: '2 days ago',
    pages: 6,
    status: 'reviewed',
    supplier: { name: 'Nordic Kitchenware Co.', location: 'Stockholm, Sweden', email: 'sales@nordickitchenware.se', terms: 'FOB Stockholm · Net 30' },
    products: [
      { name: 'Brushed Steel Stockpot 8L', sku: 'NK-SP-08', price: '74.00', currency: '€', moq: '50', lead: '3 wks', categories: ['Cookware', 'Stainless Steel'] },
      { name: 'Acacia Cutting Board, Set of 3', sku: 'NK-CB-3S', price: '28.50', currency: '€', moq: '100', lead: '2 wks', categories: ['Kitchenware', 'Wood'] },
      { name: 'Cast Iron Skillet 26 cm', sku: 'NK-CI-26', price: '42.00', currency: '€', moq: '75', lead: '4 wks', categories: ['Cookware', 'Cast Iron'] },
      { name: 'Linen Bistro Apron', sku: 'NK-AP-01', price: '19.90', currency: '€', moq: '200', lead: '3 wks', categories: ['Textiles', 'Linen'] },
    ],
  },
  {
    id: 'c2',
    file: 'Aterra_Cookware_Pricelist_2026.pdf',
    date: '4 days ago',
    pages: 4,
    status: 'reviewed',
    supplier: { name: 'Aterra Cookware', location: 'Bilbao, Spain', email: 'ventas@aterracookware.es', terms: 'EXW Bilbao · Net 45' },
    products: [
      { name: 'Cast Iron Skillet 28 cm', sku: 'AT-CI-28', price: '38.00', currency: '€', moq: '60', lead: '5 wks', categories: ['Cookware', 'Cast Iron'] },
      { name: 'Stainless Stockpot 6L', sku: 'AT-SP-06', price: '61.00', currency: '€', moq: '40', lead: '4 wks', categories: ['Cookware', 'Stainless Steel'] },
      { name: 'Carbon Steel Frying Pan 24 cm', sku: 'AT-FP-24', price: '31.50', currency: '€', moq: '80', lead: '3 wks', categories: ['Cookware'] },
      { name: 'Saucepan 2L with Lid', sku: 'AT-SC-02', price: '24.00', currency: '€', moq: '100', lead: '3 wks', categories: ['Cookware', 'Stainless Steel'] },
    ],
  },
  {
    id: 'c3',
    file: 'Hesse_Roth_Tabletop_Q1.pdf',
    date: '1 week ago',
    pages: 8,
    status: 'in_review',
    supplier: { name: 'Hesse & Roth GmbH', location: 'Solingen, Germany', email: 'export@hesse-roth.de', terms: 'FCA Solingen · Net 30' },
    products: [
      { name: 'Cast Iron Skillet 24 cm', sku: 'HR-CI-24', price: '47.00', currency: '€', moq: '50', lead: '6 wks', categories: ['Cookware', 'Cast Iron'] },
      { name: 'Stainless Stockpot 10L', sku: 'HR-SP-10', price: '89.00', currency: '€', moq: '30', lead: '5 wks', categories: ['Cookware', 'Stainless Steel'] },
      { name: 'Forged Chef Knife 20 cm', sku: 'HR-CK-20', price: '58.00', currency: '€', moq: '40', lead: '6 wks', categories: ['Cutlery'] },
      { name: 'Walnut Cutting Board', sku: 'HR-CB-01', price: '34.00', currency: '€', moq: '60', lead: '4 wks', categories: ['Kitchenware', 'Wood'] },
    ],
  },
  {
    id: 'c4',
    file: 'Meridian_Glassware_Pricelist_Q2.pdf',
    date: '5 days ago',
    pages: 3,
    status: 'reviewed',
    supplier: { name: 'Meridian Glassware', location: 'Porto, Portugal', email: 'trade@meridianglass.pt', terms: 'FOB Porto · Net 30' },
    products: [
      { name: 'Crystal Wine Glass, Set of 6', sku: 'MG-WG-6', price: '33.00', currency: '€', moq: '120', lead: '4 wks', categories: ['Glassware', 'Tableware'] },
      { name: 'Tumbler, Set of 4', sku: 'MG-TU-4', price: '18.00', currency: '€', moq: '150', lead: '3 wks', categories: ['Glassware', 'Tableware'] },
      { name: 'Glass Carafe 1.2L', sku: 'MG-CA-12', price: '22.50', currency: '€', moq: '100', lead: '3 wks', categories: ['Glassware'] },
      { name: 'Cast Iron Trivet', sku: 'MG-TR-01', price: '14.00', currency: '€', moq: '90', lead: '4 wks', categories: ['Cookware', 'Cast Iron'] },
    ],
  },
  {
    id: 'c5',
    file: 'Lin_Flax_Linens_2026.pdf',
    date: '1 week ago',
    pages: 5,
    status: 'in_review',
    supplier: { name: 'Lin & Flax', location: 'Ghent, Belgium', email: 'hello@linandflax.be', terms: 'EXW Ghent · Net 30' },
    products: [
      { name: 'Linen Bistro Apron', sku: 'LF-AP-02', price: '17.50', currency: '€', moq: '250', lead: '4 wks', categories: ['Textiles', 'Linen'] },
      { name: 'Linen Tea Towels, Set of 3', sku: 'LF-TT-3', price: '12.00', currency: '€', moq: '300', lead: '3 wks', categories: ['Textiles', 'Linen'] },
      { name: 'Linen Table Runner', sku: 'LF-TR-01', price: '26.00', currency: '€', moq: '150', lead: '5 wks', categories: ['Textiles', 'Linen'] },
    ],
  },
];

export const DEMO_DATA = {
  supplier: {
    name: 'Nordic Kitchenware Co.',
    contact: 'Astrid Lindqvist',
    email: 'sales@nordickitchenware.se',
    phone: '+46 8 559 21 040',
    location: 'Stockholm, Sweden',
    terms: 'FOB Stockholm · Net 30',
    conf: { name: 'high', contact: 'high', email: 'med', phone: 'high', location: 'high', terms: 'med' },
  },
  products: [
    { id: 'p1', name: 'Brushed Steel Stockpot 8L', sku: 'NK-SP-08', price: '74.00', currency: '€', moq: '50', specs: '18/10 stainless steel · triple-ply base · 24 cm Ø · induction ready', categories: ['Cookware', 'Stainless Steel'], reviewed: false, conf: { name: 'high', sku: 'high', price: 'high', moq: 'high', specs: 'high' } },
    { id: 'p2', name: 'Acacia Cutting Board, Set of 3', sku: 'NK-CB-3S', price: '28.50', currency: '€', moq: '100', specs: 'FSC-certified acacia · food-safe oil finish · three nesting sizes', categories: ['Kitchenware', 'Wood'], reviewed: false, conf: { name: 'high', sku: 'high', price: 'low', moq: 'high', specs: 'med' } },
    { id: 'p3', name: 'Cast Iron Skillet 26 cm', sku: 'NK-CI-26', price: '42.00', currency: '€', moq: '75', specs: 'Pre-seasoned · pour spouts both sides · oven-safe to 260°C', categories: ['Cookware', 'Cast Iron'], reviewed: false, conf: { name: 'high', sku: 'med', price: 'high', moq: 'high', specs: 'high' } },
    { id: 'p4', name: 'Linen Bistro Apron', sku: 'NK-AP-01', price: '19.90', currency: '€', moq: '200', specs: '100% European flax · adjustable neck strap · twin front pockets', categories: ['Textiles', 'Linen'], reviewed: false, conf: { name: 'med', sku: 'high', price: 'high', moq: 'med', specs: 'high' } },
  ],
};

export const PROCESSING_STEPS = [
  'Parsing document layout',
  'Detecting supplier details',
  'Extracting product entries',
  'Retrieving product images',
  'Categorizing & normalizing prices',
];
