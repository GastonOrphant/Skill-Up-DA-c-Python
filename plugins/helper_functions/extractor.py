from airflow.providers.postgres.hooks.postgres import PostgresHook

class Extractor:
    def __init__(self, university, logger=None) -> None:
        self.university = university
        self.logger = logger

    def extraction(self):     
        # Lee el archivo .sql con el query para consultar los datos de la universidad
        with open(f'./include/{self.university}.sql','r', encoding='utf-8') as f:
            sql_script = f.read()

        # Inicia el hook a Postgres para conectar a la base de datos
        hook = PostgresHook(postgres_conn_id="alkemy_db")

        # Se crea el dataframe y lo exporta a la carpeta files
        df = hook.get_pandas_df(sql=sql_script)
        df.to_csv(f"./files/{self.university}_select.csv")

    def to_extract(self):
        if self.logger:
            self.logger.info('Inicio de proceso de extracción')
        try:
            self.extraction()
            if self.logger:
                self.logger.info("Se creo el csv con la información de la universidad")

        except Exception as e:
            if self.logger:
                self.logger.info('ERROR al extraer los datos')
                self.logger.error(e)

